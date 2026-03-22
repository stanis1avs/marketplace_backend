from django.contrib import admin
from .models import Category, Product, Size


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'title']
    search_fields = ['title']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'category', 'color', 'current_price']
    list_filter = ['category', 'season']
    search_fields = ['title', 'color']

    def current_price(self, obj):
        price = obj.prices.order_by("-fetched_at").first()
        return price.price if price else None


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ['product', 'size', 'available']
    list_filter = ['size', 'available']
