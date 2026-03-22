from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Prefetch
from django.conf import settings
from .models import Product, Category, Size
import json


@csrf_exempt
@require_http_methods(["GET"])
def top_sales(request):
    """Get top sale products"""
    top_sales = Product.objects.filter(
        id__in=settings.TOP_SALE_IDS
    ).select_related('category').prefetch_related(
        'prices_set'
    )
    
    result = []
    for product in top_sales:
        latest_price = product.prices_set.order_by('-fetched_at').first()
        
        try:
            images = json.loads(product.images) if product.images else []
        except (json.JSONDecodeError, TypeError):
            images = []
        
        item_data = {
            'id': product.id,
            'title': product.title,
            'price': float(latest_price.price) if latest_price else 0,
            'images': images
        }
        result.append(item_data)
    
    return JsonResponse(result, safe=False, json_dumps_params={'ensure_ascii': False})


@csrf_exempt
@require_http_methods(["GET"])
def categories(request):
    """Get all categories"""
    categories = Category.objects.all().values()
    return JsonResponse(list(categories), safe=False)


@csrf_exempt
@require_http_methods(["GET"])
def items(request):
    """Search products with pagination"""
    query = request.GET.get('q', '').strip().lower()
    category_id = request.GET.get('categoryId', '0')
    offset = int(request.GET.get('offset', 0))
    
    q_filter = Q()
    if query:
        q_filter = Q(title__icontains=query) | Q(color__icontains=query)
    
    category_filter = Q()
    if category_id != '0':
        category_filter = Q(category_id=category_id)
    
    items = Product.objects.filter(
        q_filter & category_filter
    ).select_related('category').prefetch_related(
        'prices_set'
    )[
        offset:offset + settings.MORE_COUNT
    ]
    
    result = []
    for product in items:
        latest_price = product.prices_set.order_by('-fetched_at').first()
        
        try:
            images = json.loads(product.images) if product.images else []
        except (json.JSONDecodeError, TypeError):
            images = []
        
        item_data = {
            'id': product.id,
            'category': product.category.title,
            'title': product.title,
            'price': float(latest_price.price) if latest_price else 0,
            'images': images
        }
        result.append(item_data)
    
    return JsonResponse(result, safe=False, json_dumps_params={'ensure_ascii': False})


@csrf_exempt
@require_http_methods(["GET"])
def item_detail(request, item_id):
    """Get product details with sizes"""
    
    try:
        product = Product.objects.filter(id=item_id).select_related('category').prefetch_related(
            'prices_set',
            Prefetch('size_set', queryset=Size.objects.all())
        ).first()
        
        if not product:
            return JsonResponse({'error': 'Not found'}, status=404)
        
        sizes = product.size_set.all()
        sizes_list = [{'size': size.size, 'available': size.available} for size in sizes]
        
        latest_price = product.prices_set.order_by('-fetched_at').first()
        
        try:
            images = json.loads(product.images) if product.images else []
        except (json.JSONDecodeError, TypeError):
            images = []
        
        item_data = {
            'id': product.id,
            'title': product.title,
            'price': float(latest_price.price) if latest_price else 0,
            'color': product.color,
            'material': product.material,
            'season': product.season,
            'images': images,
            'category': product.category.title,
            'sku': product.sku,
            'manufacturer': product.manufacturer,
            'reason': product.reason,
            'sizes': sizes_list
        }
        
        return JsonResponse(item_data, json_dumps_params={'ensure_ascii': False})
        
    except Exception as e:
        return JsonResponse({'error': 'Not found'}, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def order(request):
    """Process order"""
    try:
        data = json.loads(request.body)
        owner = data.get('owner', {})
        items = data.get('items', [])
        
        phone = owner.get('phone')
        address = owner.get('address')
        
        if not isinstance(phone, str):
            return JsonResponse({'error': 'Bad Request: Phone'}, status=400)
        
        if not isinstance(address, str):
            return JsonResponse({'error': 'Bad Request: Address'}, status=400)
        
        if not isinstance(items, list):
            return JsonResponse({'error': 'Bad Request: Items'}, status=400)
        
        for item in items:
            if not all([
                isinstance(item.get('id'), (int, float)) and item.get('id') > 0,
                isinstance(item.get('price'), (int, float)) and item.get('price') > 0,
                isinstance(item.get('count'), (int, float)) and item.get('count') > 0
            ]):
                return JsonResponse({'error': 'Bad Request'}, status=400)

        return HttpResponse(status=204)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Bad Request'}, status=400)
    except Exception as e:
        return JsonResponse({'error': 'Bad Request'}, status=400)
