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
    ).values('id', 'title', 'price', 'images')
    
    # Parse images field for each item
    result = []
    for item in top_sales:
        item_dict = dict(item)
        result.append(item_dict)
    
    return JsonResponse(result, safe=False)


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
    ).values('id', 'category', 'title', 'price', 'images')[
        offset:offset + settings.MORE_COUNT
    ]
    
    # Parse images field for each item
    result = []
    for item in items:
        item_dict = dict(item)
        result.append(item_dict)
    
    return JsonResponse(result, safe=False)


@csrf_exempt
@require_http_methods(["GET"])
def item_detail(request, item_id):
    """Get product details with sizes"""
    
    try:
        product = Product.objects.filter(id=item_id).first()
        
        if not product:
            return JsonResponse({'error': 'Not found'}, status=404)
        
        sizes = Size.objects.filter(product_id=item_id).values('size', 'available')
        sizes_list = [{'size': size['size'], 'available': size['available']} for size in sizes]
        
        item_data = {
            'id': product.id,
            'title': product.title,
            'price': float(product.price),
            'color': product.color,
            'material': product.material,
            'season': product.season,
            'images': product.images,
            'category': product.category_id,
            'sku': product.sku,
            'manufacturer': product.manufacturer,
            'reason': product.reason,
            'sizes': sizes_list
        }
        
        return JsonResponse(item_data)
        
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
        
        # Validation
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
        
        # Order processing logic would go here
        # For now, just return success
        return HttpResponse(status=204)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Bad Request'}, status=400)
    except Exception as e:
        return JsonResponse({'error': 'Bad Request'}, status=400)
