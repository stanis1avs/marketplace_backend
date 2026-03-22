from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Product, Size, FeedSource, Prices 


class Command(BaseCommand):
    help = "Fix product ids and move old id to source_product_id"

    @transaction.atomic
    def handle(self, *args, **kwargs):

        default_source = FeedSource.objects.first()

        products = list(Product.objects.all().order_by("id"))

        count = 0

        for product in products:

            old_id = product.id

            new_product = Product.objects.create(
                source=default_source if product.manufacturer.lower() == 'fable' else product.source,
                source_product_id=str(old_id),
                title=product.title,
                sku=product.sku,
                manufacturer=product.manufacturer,
                color=product.color,
                material=product.material,
                season=product.season,
                reason=product.reason,
                images=product.images,
                category=product.category,
            )

            new_id = new_product.id

            Size.objects.filter(product_id=old_id).update(product_id=new_id)
            Prices.objects.filter(product_id=old_id).update(product_id=new_id)

            product.delete()

            count += 1

            if count % 1000 == 0:
                self.stdout.write(f"Processed {count}")

        self.stdout.write(self.style.SUCCESS(f"Done: {count} products"))