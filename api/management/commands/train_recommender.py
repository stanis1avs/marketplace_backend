"""
Train recommender models and precompute recommendations to PostgreSQL.

Usage:
    python manage.py train_recommender --strategy content    # cold-start, no user data needed
    python manage.py train_recommender --strategy all        # full pipeline
    python manage.py train_recommender --strategy collaborative
    python manage.py train_recommender --strategy cart
"""
import numpy as np
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import OuterRef, Subquery
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity
from api.models import Product, ProductRecommendation, Prices, UserInteraction, CartItem, UserRecommendation

class Command(BaseCommand):
    help = 'Train recommender models and precompute recommendations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--strategy',
            choices=['all', 'content', 'collaborative', 'cart'],
            default='all',
        )
        parser.add_argument('--top-k', type=int, default=12)

    def handle(self, *args, **options):
        strategy = options['strategy']
        top_k = options['top_k']

        if strategy in ('all', 'content'):
            self.stdout.write('→ Running content-based recommendations...')
            self._run_content_based(top_k)

        if strategy in ('all', 'collaborative'):
            self.stdout.write('→ Running collaborative filtering (TF Recommenders)...')
            self._run_collaborative(top_k)

        if strategy in ('all', 'cart'):
            self.stdout.write('→ Running cart-based recommendations...')
            self._run_cart_based(top_k)

        self.stdout.write(self.style.SUCCESS('Done.'))

    # ── Content-based ─────────────────────────────────────────────────────────

    def _run_content_based(self, top_k):
        # Annotate each product with its latest price via subquery
        latest_price_sq = Subquery(
            Prices.objects.filter(product=OuterRef('pk'))
            .order_by('-fetched_at')
            .values('price')[:1]
        )

        products = list(
            Product.objects.all()
            .annotate(latest_price=latest_price_sq)
            .values('id', 'category_id', 'color', 'material', 'season', 'reason', 'latest_price')
        )

        if len(products) < 2:
            self.stdout.write(self.style.WARNING('Not enough products for content-based.'))
            return

        ids = [p['id'] for p in products]
        cat_features = []

        for field in ('category_id', 'color', 'material', 'season', 'reason'):
            values = [str(p[field] or '') for p in products]
            enc = LabelEncoder()
            encoded = enc.fit_transform(values).reshape(-1, 1)
            cat_features.append(encoded)

        prices = np.array([[float(p['latest_price'] or 0)] for p in products])
        scaler = MinMaxScaler()
        prices_norm = scaler.fit_transform(prices)

        feature_matrix = np.hstack(cat_features + [prices_norm]).astype(float)
        sim_matrix = cosine_similarity(feature_matrix)

        to_create = []
        for i, source_id in enumerate(ids):
            row = sim_matrix[i]
            top_indices = np.argsort(row)[::-1]
            count = 0
            for j in top_indices:
                if j == i:
                    continue
                to_create.append(ProductRecommendation(
                    source_product_id=source_id,
                    target_product_id=ids[j],
                    score=float(row[j]),
                    strategy='content',
                ))
                count += 1
                if count >= top_k:
                    break

        self._bulk_upsert_product_recs(to_create, 'content')
        self.stdout.write(f'  Content-based: wrote {len(to_create)} recommendations.')

    # ── Collaborative (TF Recommenders two-tower) ─────────────────────────────

    def _run_collaborative(self, top_k):
        """
        Two-tower collaborative filtering using pure TensorFlow + Keras (no tensorflow_recommenders).
        tensorflow_recommenders is incompatible with Keras 3.x / TF 2.16+.
        Retrieval is done via numpy dot-product cosine similarity after training.
        """
        interactions = list(UserInteraction.objects.values('user_id', 'product_id', 'weight'))
        cart_signals = list(CartItem.objects.values('cart__user_id', 'product_id'))
        for cs in cart_signals:
            interactions.append({
                'user_id': cs['cart__user_id'],
                'product_id': cs['product_id'],
                'weight': 3.0,
            })

        if len(interactions) < 50:
            self.stdout.write(self.style.WARNING(
                f'  Only {len(interactions)} interactions — need 50+ for collaborative filtering. Skipping.'
            ))
            return

        try:
            import tensorflow as tf
        except ImportError:
            self.stdout.write(self.style.ERROR('  tensorflow not installed.'))
            return

        user_ids = sorted({str(i['user_id']) for i in interactions})
        product_ids = sorted({str(p) for p in Product.objects.values_list('id', flat=True)})
        embedding_dim = 32

        def make_tower(vocab):
            return tf.keras.Sequential([
                tf.keras.layers.StringLookup(vocabulary=vocab, mask_token=None),
                tf.keras.layers.Embedding(len(vocab) + 1, embedding_dim),
                tf.keras.layers.Dense(64, activation='relu'),
                tf.keras.layers.Dense(embedding_dim),
            ])

        user_tower = make_tower(user_ids)
        product_tower = make_tower(product_ids)
        optimizer = tf.keras.optimizers.Adagrad(learning_rate=0.1)

        u_data = tf.constant([str(i['user_id']) for i in interactions])
        p_data = tf.constant([str(i['product_id']) for i in interactions])
        dataset = tf.data.Dataset.from_tensor_slices((u_data, p_data)) \
            .shuffle(len(interactions)).batch(256)

        # Training: in-batch softmax cross-entropy (standard two-tower loss)
        for epoch in range(10):
            epoch_loss = 0.0
            steps = 0
            for u_batch, p_batch in dataset:
                with tf.GradientTape() as tape:
                    u_emb = user_tower(u_batch, training=True)      # (B, dim)
                    p_emb = product_tower(p_batch, training=True)    # (B, dim)
                    logits = tf.matmul(u_emb, p_emb, transpose_b=True)  # (B, B)
                    labels = tf.eye(tf.shape(logits)[0])
                    loss = tf.reduce_mean(
                        tf.nn.softmax_cross_entropy_with_logits(labels=labels, logits=logits)
                    )
                grads = tape.gradient(
                    loss,
                    user_tower.trainable_variables + product_tower.trainable_variables,
                )
                optimizer.apply_gradients(zip(
                    grads,
                    user_tower.trainable_variables + product_tower.trainable_variables,
                ))
                epoch_loss += float(loss)
                steps += 1
            if epoch % 3 == 0:
                self.stdout.write(f'    epoch {epoch + 1}/10  loss={epoch_loss / max(steps, 1):.4f}')

        # Inference: embed all products → cosine similarity with each user
        all_p_emb = product_tower(tf.constant(product_ids), training=False).numpy()
        norms = np.linalg.norm(all_p_emb, axis=1, keepdims=True)
        all_p_emb = all_p_emb / np.where(norms == 0, 1e-8, norms)

        to_create = []
        for uid_str in user_ids:
            u_emb = user_tower(tf.constant([uid_str]), training=False).numpy()[0]
            u_norm = np.linalg.norm(u_emb)
            u_emb = u_emb / (u_norm if u_norm > 1e-8 else 1e-8)
            scores = all_p_emb @ u_emb                           # (N_products,)
            top_indices = np.argsort(scores)[::-1][:top_k]
            user_id = int(uid_str)
            for idx in top_indices:
                to_create.append(UserRecommendation(
                    user_id=user_id,
                    product_id=int(product_ids[idx]),
                    score=float(scores[idx]),
                    strategy='collaborative',
                ))

        self._bulk_upsert_user_recs(to_create)
        self.stdout.write(f'  Collaborative: wrote {len(to_create)} user recommendations.')

    # ── Cart-based ────────────────────────────────────────────────────────────

    def _run_cart_based(self, top_k):
        """
        For each product, precompute top-k nearest neighbours using content feature cosine similarity.
        (tf.saved_model is incompatible with Keras 3.x; product tower embeddings are not persisted.)
        """
        # Reuse the same feature matrix as content-based
        latest_price_sq = Subquery(
            Prices.objects.filter(product=OuterRef('pk'))
            .order_by('-fetched_at')
            .values('price')[:1]
        )
        products = list(
            Product.objects.all()
            .annotate(latest_price=latest_price_sq)
            .values('id', 'category_id', 'color', 'material', 'season', 'reason', 'latest_price')
        )

        if len(products) < 2:
            self.stdout.write(self.style.WARNING('Not enough products for cart-based.'))
            return

        product_ids = [p['id'] for p in products]
        cat_features = []
        for field in ('category_id', 'color', 'material', 'season', 'reason'):
            values = [str(p[field] or '') for p in products]
            enc = LabelEncoder()
            cat_features.append(enc.fit_transform(values).reshape(-1, 1))

        prices = np.array([[float(p['latest_price'] or 0)] for p in products])
        prices_norm = MinMaxScaler().fit_transform(prices)

        feature_matrix = np.hstack(cat_features + [prices_norm]).astype(float)
        norms = np.linalg.norm(feature_matrix, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1e-8, norms)
        normed = feature_matrix / norms
        sim_matrix = normed @ normed.T

        to_create = []
        for i, source_id in enumerate(product_ids):
            row = sim_matrix[i]
            top_indices = np.argsort(row)[::-1]
            count = 0
            for j in top_indices:
                if j == i:
                    continue
                to_create.append(ProductRecommendation(
                    source_product_id=source_id,
                    target_product_id=product_ids[j],
                    score=float(row[j]),
                    strategy='cart',
                ))
                count += 1
                if count >= top_k:
                    break

        self._bulk_upsert_product_recs(to_create, 'cart')
        self.stdout.write(f'  Cart-based: wrote {len(to_create)} recommendations.')

    # ── DB helpers ────────────────────────────────────────────────────────────

    def _bulk_upsert_product_recs(self, records, strategy):
        if not records:
            return
        with transaction.atomic():
            ProductRecommendation.objects.filter(strategy=strategy).delete()
            batch_size = 500
            for i in range(0, len(records), batch_size):
                ProductRecommendation.objects.bulk_create(
                    records[i:i + batch_size],
                    ignore_conflicts=True,
                )

    def _bulk_upsert_user_recs(self, records):
        if not records:
            return
        user_ids = {r.user_id for r in records}
        with transaction.atomic():
            UserRecommendation.objects.filter(
                user_id__in=user_ids, strategy='collaborative'
            ).delete()
            batch_size = 500
            for i in range(0, len(records), batch_size):
                UserRecommendation.objects.bulk_create(
                    records[i:i + batch_size],
                    ignore_conflicts=True,
                )
