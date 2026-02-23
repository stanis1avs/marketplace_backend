from django.urls import path
from . import views

urlpatterns = [
    path('top-sales/', views.top_sales, name='top-sales'),
    path('categories/', views.categories, name='categories'),
    path('items/<int:item_id>/', views.item_detail, name='item-detail'),
    path('items/', views.items, name='items'),
    path('order/', views.order, name='order'),
]
