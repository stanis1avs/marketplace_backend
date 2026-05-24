"""
Check collaborative filtering results per user.

Usage:
    python manage.py check_recommendations
    python manage.py check_recommendations --users alice bob carol
    python manage.py check_recommendations --strategy content --product-id 52343
"""
from django.core.management.base import BaseCommand
from api.models import UserRecommendation, ProductRecommendation, MarketplaceUser


class Command(BaseCommand):
    help = 'Display precomputed recommendations for users or products'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            nargs='+',
            default=['alice', 'bob', 'dave'],
            help='Usernames to check (default: alice bob dave)',
        )
        parser.add_argument(
            '--strategy',
            choices=['collaborative', 'content', 'cart'],
            default='collaborative',
        )
        parser.add_argument(
            '--product-id',
            type=int,
            help='Show product recommendations for this product ID (content/cart strategies)',
        )
        parser.add_argument('--top-k', type=int, default=6)

    def handle(self, *args, **options):
        strategy = options['strategy']
        top_k = options['top_k']

        if options['product_id']:
            recs = (
                ProductRecommendation.objects
                .filter(source_product_id=options['product_id'], strategy=strategy)
                .order_by('-score')
                .values_list('target_product_id', 'score')[:top_k]
            )
            self.stdout.write(f"\nProduct {options['product_id']} → [{strategy}]:")
            for pid, score in recs:
                self.stdout.write(f'  {pid}  score={score:.4f}')
            if not recs:
                self.stdout.write(self.style.WARNING('  No recommendations found. Run train_recommender first.'))
            return

        for username in options['users']:
            try:
                user = MarketplaceUser.objects.get(username=username)
            except MarketplaceUser.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'  User "{username}" not found.'))
                continue

            recs = (
                UserRecommendation.objects
                .filter(user=user, strategy=strategy)
                .order_by('-score')
                .values_list('product_id', 'score')[:top_k]
            )

            ids = [str(pid) for pid, _ in recs]
            self.stdout.write(f'{username}: [{", ".join(ids)}]')

        if not any(
            UserRecommendation.objects.filter(strategy=strategy).exists()
            for _ in [1]
        ):
            self.stdout.write(self.style.WARNING(
                f'\nNo {strategy} recommendations in DB. Run: python manage.py train_recommender --strategy {strategy}'
            ))
