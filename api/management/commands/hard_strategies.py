"""
Seed the DB with synthetic user interactions for testing strategies 2 & 3.

Usage:
    python manage.py test_hard_strategies
    python manage.py test_hard_strategies --clear   # drop existing interactions first
"""
import random
from django.core.management.base import BaseCommand
from api.models import MarketplaceUser, UserInteraction, Product


class Command(BaseCommand):
    help = 'Generate synthetic interactions for collaborative filtering tests'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete existing UserInteraction rows before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            deleted, _ = UserInteraction.objects.all().delete()
            self.stdout.write(f'  Cleared {deleted} existing interactions.')

        product_ids = list(Product.objects.values_list('id', flat=True))
        if len(product_ids) < 10:
            self.stdout.write(self.style.ERROR('Need at least 10 products in DB.'))
            return

        # Each user has a "taste zone" — overlapping ranges create collaborative signal
        user_behaviors = {
            'alice': product_ids[:20],
            'bob':   product_ids[5:25],   # overlaps alice → similar recs expected
            'carol': product_ids[15:35],  # overlaps bob
            'dave':  product_ids[30:50],  # different zone
            'eve':   product_ids[:10] + product_ids[40:50],  # mixed
        }

        interactions = []
        for username, prods in user_behaviors.items():
            user, created = MarketplaceUser.objects.get_or_create(username=username)
            if created:
                self.stdout.write(f'  Created user: {username}')

            for pid in prods:
                interactions.append(UserInteraction(
                    user=user, product_id=pid, event_type='view', weight=1.0
                ))

            for pid in random.sample(prods, max(1, len(prods) // 2)):
                interactions.append(UserInteraction(
                    user=user, product_id=pid, event_type='cart_add', weight=3.0
                ))

            for pid in random.sample(prods, min(3, len(prods))):
                interactions.append(UserInteraction(
                    user=user, product_id=pid, event_type='order', weight=5.0
                ))

        UserInteraction.objects.bulk_create(interactions)
        self.stdout.write(self.style.SUCCESS(
            f'Done. Created {len(interactions)} interactions for {len(user_behaviors)} users.'
        ))
        self.stdout.write('Next step: python manage.py train_recommender --strategy collaborative')
