from django.db import models
import uuid

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