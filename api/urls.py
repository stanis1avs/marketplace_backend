from django.urls import path
from . import views

urlpatterns = [
    # Existing
    path('top-sales/', views.top_sales, name='top-sales'),
    path('categories/', views.categories, name='categories'),
    path('items/<int:item_id>/', views.item_detail, name='item-detail'),
    path('items/', views.items, name='items'),
    path('order/', views.order, name='order'),

    # Auth (Passkeys / WebAuthn)
    path('auth/register/begin/', views.auth_register_begin, name='auth-register-begin'),
    path('auth/register/complete/', views.auth_register_complete, name='auth-register-complete'),
    path('auth/login/begin/', views.auth_login_begin, name='auth-login-begin'),
    path('auth/login/complete/', views.auth_login_complete, name='auth-login-complete'),
    path('auth/logout/', views.auth_logout, name='auth-logout'),
    path('auth/me/', views.auth_me, name='auth-me'),

    # Cart
    path('cart/', views.cart_view, name='cart'),
    path('cart/<int:item_id>/', views.cart_item_view, name='cart-item'),

    # Interactions & Recommendations
    path('interactions/', views.interactions, name='interactions'),
    path('recommendations/', views.recommendations, name='recommendations'),
]
