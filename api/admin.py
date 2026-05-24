from django.contrib import admin
from .models import (
    FeedSource, Category, Product, Size, Prices, RawFeedFile,
    MarketplaceUser, WebAuthnCredential, Session,
    Cart, CartItem,
    UserInteraction, Order, OrderItem,
    ProductRecommendation, UserRecommendation,
)


@admin.register(FeedSource)
class FeedSourceAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'feed_url']
    search_fields = ['name']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'parsed_category']
    search_fields = ['title']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'category', 'color', 'current_price']
    list_filter = ['category', 'season']
    search_fields = ['title', 'color']

    def current_price(self, obj):
        price = obj.prices_set.order_by('-fetched_at').first()
        return price.price if price else None


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ['product', 'size', 'available']
    list_filter = ['size', 'available']


@admin.register(Prices)
class PricesAdmin(admin.ModelAdmin):
    list_display = ['id', 'product', 'price', 'currency', 'fetched_at']
    list_filter = ['currency']


@admin.register(RawFeedFile)
class RawFeedFileAdmin(admin.ModelAdmin):
    list_display = ['id', 'source', 'fetched_at', 'filename', 'size']


@admin.register(MarketplaceUser)
class MarketplaceUserAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'created_at', 'last_login']
    search_fields = ['username']


@admin.register(WebAuthnCredential)
class WebAuthnCredentialAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'credential_id', 'sign_count', 'created_at']
    search_fields = ['user__username']


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'created_at', 'expires_at']
    search_fields = ['user__username']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'updated_at']
    search_fields = ['user__username']


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'cart', 'product', 'size', 'count', 'added_at']


@admin.register(UserInteraction)
class UserInteractionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'product', 'event_type', 'weight', 'created_at']
    list_filter = ['event_type']
    search_fields = ['user__username']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'phone', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['user__username', 'phone']


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'product', 'price', 'count', 'size']


@admin.register(ProductRecommendation)
class ProductRecommendationAdmin(admin.ModelAdmin):
    list_display = ['id', 'source_product', 'target_product', 'score', 'strategy', 'updated_at']
    list_filter = ['strategy']


@admin.register(UserRecommendation)
class UserRecommendationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'product', 'score', 'strategy', 'updated_at']
    list_filter = ['strategy']
    search_fields = ['user__username']
