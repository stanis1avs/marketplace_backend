from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Product, Prices


class Command(BaseCommand):
    help = "Move price from Product.price to Price table"

    @transaction.atomic
    def handle(self, *args, **kwargs):

        products = Product.objects.all()

        count = 0

        for product in products:

            if product.price is None:
                continue

            price_obj = Prices.objects.create(
                price=product.price, product=product
            )

            count += 1

            if count % 1000 == 0:
                self.stdout.write(f"Processed {count} products")

        self.stdout.write(self.style.SUCCESS(f"Migration completed. {count} products updated"))