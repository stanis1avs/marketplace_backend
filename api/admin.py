from django.contrib import admin
from .models import Category, Product, Size


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'title']
    search_fields = ['title']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'price', 'category', 'color']
    list_filter = ['category', 'season']
    search_fields = ['title', 'color']


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ['product', 'size', 'available']
    list_filter = ['size', 'available']
