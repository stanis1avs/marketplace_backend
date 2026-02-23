from django.db import models


class Category(models.Model):
    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=255)

    class Meta:
        db_table = 'categories'

    def __str__(self):
        return self.title


class Product(models.Model):
    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=255)
    sku = models.CharField(max_length=255)
    manufacturer = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    color = models.CharField(max_length=100, blank=True, null=True)
    material = models.CharField(max_length=100, blank=True, null=True)
    season = models.CharField(max_length=50, blank=True, null=True)
    reason = models.CharField(max_length=255, blank=True, null=True)
    images = models.TextField(default='[]')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, db_column='category')

    class Meta:
        db_table = 'products'

    def __str__(self):
        return self.title


class Size(models.Model):
    id = models.AutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, db_column='productid')
    size = models.CharField(max_length=10)
    available = models.BooleanField(db_column='avalible')

    class Meta:
        db_table = 'sizes'
        unique_together = ['product', 'size']

    def __str__(self):
        return f"{self.product.title} - {self.size}"
