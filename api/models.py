import secrets
import uuid
from django.db import models
from django.utils import timezone
from datetime import timedelta


# ── Existing models (unchanged) ───────────────────────────────────────────────

class FeedSource(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    feed_url = models.TextField()
    note = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'feed_sources'

    def __str__(self):
        return f"{self.name}"


class Category(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    parsed_category = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'categories'

    def __str__(self):
        return self.title


class Product(models.Model):
    id = models.AutoField(primary_key=True)
    source = models.ForeignKey(FeedSource, on_delete=models.CASCADE, db_column='source', null=True)
    source_product_id = models.CharField(max_length=255, null=True)
    title = models.CharField(max_length=255)
    sku = models.CharField(max_length=255)
    manufacturer = models.CharField(max_length=255)
    color = models.CharField(max_length=100, blank=True, null=True)
    material = models.CharField(max_length=100, blank=True, null=True)
    season = models.CharField(max_length=50, blank=True, null=True)
    reason = models.CharField(max_length=255, blank=True, null=True)
    images = models.TextField(default='[]')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, db_column='category')

    class Meta:
        db_table = 'products'
        indexes = [
            models.Index(fields=["source", "source_product_id"])
        ]

    def __str__(self):
        return self.title


class Size(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, db_column='productid')
    size = models.CharField(max_length=10)
    available = models.BooleanField(db_column='avalible')

    class Meta:
        db_table = 'sizes'
        unique_together = ['product', 'size']

    def __str__(self):
        return f"{self.product.title} - {self.size}"


class Prices(models.Model):
    id = models.AutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    max_price = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    min_price = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    currency = models.CharField(max_length=10, default='RUB')
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'prices'
        indexes = [
            models.Index(fields=['product', 'fetched_at']),
        ]

    def __str__(self):
        return f"{self.product.id} @ {self.price}"


class RawFeedFile(models.Model):
    id = models.AutoField(primary_key=True)
    source = models.ForeignKey(FeedSource, on_delete=models.SET_NULL, null=True)
    fetched_at = models.DateTimeField(auto_now_add=True)
    filename = models.CharField(max_length=512, blank=True, null=True)
    sha256 = models.CharField(max_length=128, blank=True, null=True)
    size = models.BigIntegerField(null=True)
    local_path = models.CharField(max_length=1024, blank=True, null=True)

    class Meta:
        db_table = 'raw_feed_files'


# ── Auth ──────────────────────────────────────────────────────────────────────

class MarketplaceUser(models.Model):
    username = models.CharField(max_length=150, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'marketplace_users'

    def __str__(self):
        return self.username


class WebAuthnCredential(models.Model):
    user = models.ForeignKey(MarketplaceUser, on_delete=models.CASCADE, related_name='credentials')
    credential_id = models.TextField(unique=True)  # base64url bytes
    public_key = models.TextField()               # base64 CBOR/COSE bytes
    sign_count = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webauthn_credentials'


class Session(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    user = models.ForeignKey(MarketplaceUser, on_delete=models.CASCADE, related_name='sessions')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'auth_sessions'

    @classmethod
    def create_for_user(cls, user, days=30):
        from django.conf import settings as django_settings
        expire_days = getattr(django_settings, 'SESSION_EXPIRE_DAYS', 30)
        return cls.objects.create(
            id=secrets.token_hex(32),
            user=user,
            expires_at=timezone.now() + timedelta(days=expire_days),
        )


# ── Cart ──────────────────────────────────────────────────────────────────────

class Cart(models.Model):
    user = models.OneToOneField(MarketplaceUser, on_delete=models.CASCADE, related_name='cart')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'carts'


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    size = models.CharField(max_length=10, blank=True)
    count = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cart_items'
        unique_together = ['cart', 'product', 'size']


# ── Interactions & Orders ─────────────────────────────────────────────────────

class UserInteraction(models.Model):
    INTERACTION_WEIGHTS = {
        'view': 1.0,
        'cart_add': 3.0,
        'order': 5.0,
    }

    user = models.ForeignKey(MarketplaceUser, on_delete=models.CASCADE, related_name='interactions')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=20)
    weight = models.FloatField(default=1.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_interactions'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['product']),
            models.Index(fields=['event_type']),
        ]


class Order(models.Model):
    user = models.ForeignKey(
        MarketplaceUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders'
    )
    phone = models.CharField(max_length=20)
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='new')

    class Meta:
        db_table = 'orders'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    count = models.PositiveIntegerField()
    size = models.CharField(max_length=10, blank=True)

    class Meta:
        db_table = 'order_items'


# ── Recommendations ───────────────────────────────────────────────────────────

class ProductRecommendation(models.Model):
    source_product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='recommendations_as_source'
    )
    target_product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='recommendations_as_target'
    )
    score = models.FloatField()
    strategy = models.CharField(max_length=20)  # 'content', 'collaborative', 'cart'
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'product_recommendations'
        unique_together = ['source_product', 'target_product', 'strategy']
        indexes = [
            models.Index(fields=['source_product', 'strategy', 'score']),
        ]


class UserRecommendation(models.Model):
    user = models.ForeignKey(
        MarketplaceUser, on_delete=models.CASCADE, related_name='recommendations'
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    score = models.FloatField()
    strategy = models.CharField(max_length=20)  # 'collaborative'
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_recommendations'
        unique_together = ['user', 'product', 'strategy']
        indexes = [
            models.Index(fields=['user', 'strategy', 'score']),
        ]
