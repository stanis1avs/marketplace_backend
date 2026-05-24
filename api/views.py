import base64
import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Prefetch
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from .models import (
    Product, Category, Size,
    MarketplaceUser, WebAuthnCredential, Session,
    Cart, CartItem,
    UserInteraction, Order, OrderItem,
    ProductRecommendation, UserRecommendation,
)


# ── base64url helpers (WebAuthn uses URL-safe base64 without padding) ─────────

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip('=')


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += '=' * padding
    return base64.urlsafe_b64decode(s)


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_user_from_request(request):
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return None
    token = auth[7:]
    try:
        session = Session.objects.select_related('user').get(id=token)
    except Session.DoesNotExist:
        return None
    if session.expires_at < timezone.now():
        session.delete()
        return None
    return session.user


def _get_latest_price(product):
    """Return the latest Prices instance for a product, or None."""
    return product.prices_set.order_by('-fetched_at').first()


def _parse_images(product):
    try:
        return json.loads(product.images) if product.images else []
    except (json.JSONDecodeError, TypeError):
        return []


def _product_response(product):
    latest_price = _get_latest_price(product)
    return {
        'id': product.id,
        'title': product.title,
        'price': float(latest_price.price) if latest_price else 0,
        'images': _parse_images(product),
    }


def _sync_cart(user, cart_items_data):
    """Merge client-side cart items into the user's DB cart on login."""
    if not cart_items_data:
        return
    cart, _ = Cart.objects.get_or_create(user=user)
    for item in cart_items_data:
        product_id = item.get('id')
        size = item.get('size', '')
        count = int(item.get('count', 1))
        if not product_id or count < 1:
            continue
        try:
            db_item = CartItem.objects.get(cart=cart, product_id=product_id, size=size)
            db_item.count += count
            db_item.save()
        except CartItem.DoesNotExist:
            CartItem.objects.create(cart=cart, product_id=product_id, size=size, count=count)


def _cart_items_response(user):
    try:
        cart = Cart.objects.prefetch_related(
            Prefetch('items', queryset=CartItem.objects.select_related('product').prefetch_related('product__prices_set'))
        ).get(user=user)
    except Cart.DoesNotExist:
        return []
    result = []
    for item in cart.items.all():
        latest_price = item.product.prices_set.order_by('-fetched_at').first()
        price = float(latest_price.price) if latest_price else 0
        result.append({
            'id': item.id,
            'product_id': item.product_id,
            'title': item.product.title,
            'price': price,
            'images': _parse_images(item.product),
            'size': item.size,
            'count': item.count,
            'result': item.count * price,
        })
    return result


# ── Existing endpoints ────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["GET"])
def top_sales(request):
    """Get top sale products"""
    top_sales = Product.objects.filter(
        id__in=settings.TOP_SALE_IDS
    ).select_related('category').prefetch_related('prices_set')

    result = []
    for product in top_sales:
        latest_price = product.prices_set.order_by('-fetched_at').first()
        result.append({
            'id': product.id,
            'title': product.title,
            'price': float(latest_price.price) if latest_price else 0,
            'images': _parse_images(product),
        })

    return JsonResponse(result, safe=False, json_dumps_params={'ensure_ascii': False})


@csrf_exempt
@require_http_methods(["GET"])
def categories(request):
    """Get all categories"""
    cats = Category.objects.all().values()
    return JsonResponse(list(cats), safe=False)


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

    products = Product.objects.filter(
        q_filter & category_filter
    ).select_related('category').prefetch_related('prices_set')[offset:offset + settings.MORE_COUNT]

    result = []
    for product in products:
        latest_price = product.prices_set.order_by('-fetched_at').first()
        result.append({
            'id': product.id,
            'category': product.category.title,
            'title': product.title,
            'price': float(latest_price.price) if latest_price else 0,
            'images': _parse_images(product),
        })

    return JsonResponse(result, safe=False, json_dumps_params={'ensure_ascii': False})


@csrf_exempt
@require_http_methods(["GET"])
def item_detail(request, item_id):
    """Get product details with sizes"""
    try:
        product = Product.objects.filter(id=item_id).select_related('category').prefetch_related(
            'prices_set',
            Prefetch('size_set', queryset=Size.objects.all()),
        ).first()

        if not product:
            return JsonResponse({'error': 'Not found'}, status=404)

        sizes_list = [
            {'size': s.size, 'available': s.available}
            for s in product.size_set.all()
        ]
        latest_price = product.prices_set.order_by('-fetched_at').first()

        return JsonResponse({
            'id': product.id,
            'title': product.title,
            'price': float(latest_price.price) if latest_price else 0,
            'color': product.color,
            'material': product.material,
            'season': product.season,
            'images': _parse_images(product),
            'category': product.category.title,
            'sku': product.sku,
            'manufacturer': product.manufacturer,
            'reason': product.reason,
            'sizes': sizes_list,
        }, json_dumps_params={'ensure_ascii': False})

    except Exception:
        return JsonResponse({'error': 'Not found'}, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def order(request):
    """Process order — persists to DB and logs interactions."""
    try:
        data = json.loads(request.body)
        owner = data.get('owner', {})
        order_items = data.get('items', [])

        phone = owner.get('phone')
        address = owner.get('address')

        if not isinstance(phone, str):
            return JsonResponse({'error': 'Bad Request: Phone'}, status=400)
        if not isinstance(address, str):
            return JsonResponse({'error': 'Bad Request: Address'}, status=400)
        if not isinstance(order_items, list):
            return JsonResponse({'error': 'Bad Request: Items'}, status=400)

        for item in order_items:
            if not all([
                isinstance(item.get('id'), (int, float)) and item.get('id') > 0,
                isinstance(item.get('price'), (int, float)) and item.get('price') > 0,
                isinstance(item.get('count'), (int, float)) and item.get('count') > 0,
            ]):
                return JsonResponse({'error': 'Bad Request'}, status=400)

        user = get_user_from_request(request)

        db_order = Order.objects.create(user=user, phone=phone, address=address)
        for item in order_items:
            product_id = int(item['id'])
            OrderItem.objects.create(
                order=db_order,
                product_id=product_id,
                price=item['price'],
                count=int(item['count']),
                size=item.get('size', ''),
            )
            if user:
                UserInteraction.objects.create(
                    user=user,
                    product_id=product_id,
                    event_type='order',
                    weight=UserInteraction.INTERACTION_WEIGHTS['order'],
                )

        if user:
            Cart.objects.filter(user=user).delete()

        return JsonResponse({'order_id': db_order.id}, status=201)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Bad Request'}, status=400)
    except Exception:
        return JsonResponse({'error': 'Bad Request'}, status=400)


# ── Auth endpoints ────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def auth_register_begin(request):
    try:
        from webauthn import generate_registration_options, options_to_json
        from webauthn.helpers.structs import (
            AuthenticatorSelectionCriteria,
            UserVerificationRequirement,
            ResidentKeyRequirement,
        )
        from webauthn.helpers.cose import COSEAlgorithmIdentifier

        data = json.loads(request.body)
        username = data.get('username', '').strip()
        if not username:
            return JsonResponse({'error': 'username required'}, status=400)

        user, _ = MarketplaceUser.objects.get_or_create(username=username)

        from webauthn.helpers.structs import PublicKeyCredentialDescriptor
        exclude_credentials = [
            PublicKeyCredentialDescriptor(id=_b64url_decode(c.credential_id))
            for c in WebAuthnCredential.objects.filter(user=user)
        ]

        opts = generate_registration_options(
            rp_id=settings.WEBAUTHN_RP_ID,
            rp_name=settings.WEBAUTHN_RP_NAME,
            user_id=username.encode(),
            user_name=username,
            exclude_credentials=exclude_credentials,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
            supported_pub_key_algs=[
                COSEAlgorithmIdentifier.ECDSA_SHA_256,
                COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,
            ],
        )

        cache.set(
            f"webauthn_challenge_{username}",
            base64.b64encode(opts.challenge).decode(),
            timeout=300,
        )

        return HttpResponse(options_to_json(opts), content_type='application/json')

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Bad Request'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def auth_register_complete(request):
    try:
        from webauthn import verify_registration_response
        from webauthn.helpers.structs import (
            RegistrationCredential,
            AuthenticatorAttestationResponse,
        )

        data = json.loads(request.body)
        username = data.get('username', '').strip()
        credential_data = data.get('credential')
        cart_data = data.get('cart', [])

        if not username or not credential_data:
            return JsonResponse({'error': 'username and credential required'}, status=400)

        stored_b64 = cache.get(f"webauthn_challenge_{username}")
        if not stored_b64:
            return JsonResponse({'error': 'Challenge expired, try again'}, status=400)
        expected_challenge = base64.b64decode(stored_b64)

        user = MarketplaceUser.objects.filter(username=username).first()
        if not user:
            return JsonResponse({'error': 'User not found'}, status=404)

        resp = credential_data['response']
        credential = RegistrationCredential(
            id=credential_data['id'],
            raw_id=_b64url_decode(credential_data['rawId']),
            response=AuthenticatorAttestationResponse(
                client_data_json=_b64url_decode(resp['clientDataJSON']),
                attestation_object=_b64url_decode(resp['attestationObject']),
            ),
        )

        verification = verify_registration_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_rp_id=settings.WEBAUTHN_RP_ID,
            expected_origin=settings.WEBAUTHN_ORIGIN,
        )

        WebAuthnCredential.objects.create(
            user=user,
            credential_id=_b64url_encode(verification.credential_id),
            public_key=base64.b64encode(verification.credential_public_key).decode(),
            sign_count=verification.sign_count,
        )

        cache.delete(f"webauthn_challenge_{username}")
        _sync_cart(user, cart_data)
        session = Session.create_for_user(user)

        return JsonResponse({
            'token': session.id,
            'username': user.username,
            'cart': _cart_items_response(user),
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Bad Request'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def auth_login_begin(request):
    try:
        from webauthn import generate_authentication_options, options_to_json
        from webauthn.helpers.structs import (
            PublicKeyCredentialDescriptor,
            UserVerificationRequirement,
        )

        data = json.loads(request.body)
        username = data.get('username', '').strip()
        if not username:
            return JsonResponse({'error': 'username required'}, status=400)

        user = MarketplaceUser.objects.filter(username=username).first()
        if not user:
            return JsonResponse({'error': 'User not found'}, status=404)

        credentials = WebAuthnCredential.objects.filter(user=user)
        allow_credentials = [
            PublicKeyCredentialDescriptor(id=_b64url_decode(c.credential_id))
            for c in credentials
        ]

        opts = generate_authentication_options(
            rp_id=settings.WEBAUTHN_RP_ID,
            allow_credentials=allow_credentials,
            user_verification=UserVerificationRequirement.PREFERRED,
        )

        cache.set(
            f"webauthn_challenge_{username}",
            base64.b64encode(opts.challenge).decode(),
            timeout=300,
        )

        return HttpResponse(options_to_json(opts), content_type='application/json')

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Bad Request'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def auth_login_complete(request):
    try:
        from webauthn import verify_authentication_response
        from webauthn.helpers.structs import (
            AuthenticationCredential,
            AuthenticatorAssertionResponse,
        )

        data = json.loads(request.body)
        username = data.get('username', '').strip()
        credential_data = data.get('credential')
        cart_data = data.get('cart', [])

        if not username or not credential_data:
            return JsonResponse({'error': 'username and credential required'}, status=400)

        stored_b64 = cache.get(f"webauthn_challenge_{username}")
        if not stored_b64:
            return JsonResponse({'error': 'Challenge expired, try again'}, status=400)
        expected_challenge = base64.b64decode(stored_b64)

        user = MarketplaceUser.objects.filter(username=username).first()
        if not user:
            return JsonResponse({'error': 'User not found'}, status=404)

        cred_id = credential_data.get('id', '').rstrip('=')
        db_cred = WebAuthnCredential.objects.filter(user=user, credential_id=cred_id).first()
        if not db_cred:
            return JsonResponse({'error': 'Credential not found'}, status=404)

        resp = credential_data['response']
        user_handle_raw = resp.get('userHandle')
        credential = AuthenticationCredential(
            id=credential_data['id'],
            raw_id=_b64url_decode(credential_data['rawId']),
            response=AuthenticatorAssertionResponse(
                client_data_json=_b64url_decode(resp['clientDataJSON']),
                authenticator_data=_b64url_decode(resp['authenticatorData']),
                signature=_b64url_decode(resp['signature']),
                user_handle=_b64url_decode(user_handle_raw) if user_handle_raw else None,
            ),
        )

        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_rp_id=settings.WEBAUTHN_RP_ID,
            expected_origin=settings.WEBAUTHN_ORIGIN,
            credential_public_key=base64.b64decode(db_cred.public_key),
            credential_current_sign_count=db_cred.sign_count,
        )

        db_cred.sign_count = verification.new_sign_count
        db_cred.save()

        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        cache.delete(f"webauthn_challenge_{username}")
        _sync_cart(user, cart_data)
        session = Session.create_for_user(user)

        return JsonResponse({
            'token': session.id,
            'username': user.username,
            'cart': _cart_items_response(user),
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Bad Request'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def auth_logout(request):
    user = get_user_from_request(request)
    if user:
        auth = request.headers.get('Authorization', '')
        token = auth[7:]
        Session.objects.filter(id=token).delete()
    return HttpResponse(status=204)


@csrf_exempt
@require_http_methods(["GET"])
def auth_me(request):
    user = get_user_from_request(request)
    if not user:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    return JsonResponse({'id': user.id, 'username': user.username})


# ── Cart endpoints ────────────────────────────────────────────────────────────

@csrf_exempt
def cart_view(request):
    user = get_user_from_request(request)
    if not user:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    if request.method == 'GET':
        return JsonResponse(_cart_items_response(user), safe=False)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            size = data.get('size', '')
            count = int(data.get('count', 1))

            if not product_id or count < 1:
                return JsonResponse({'error': 'product_id and count required'}, status=400)

            cart, _ = Cart.objects.get_or_create(user=user)
            try:
                item = CartItem.objects.get(cart=cart, product_id=product_id, size=size)
                item.count += count
                item.save()
            except CartItem.DoesNotExist:
                CartItem.objects.create(cart=cart, product_id=product_id, size=size, count=count)

            UserInteraction.objects.create(
                user=user,
                product_id=product_id,
                event_type='cart_add',
                weight=UserInteraction.INTERACTION_WEIGHTS['cart_add'],
            )

            return JsonResponse(_cart_items_response(user), safe=False, status=201)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({'error': 'Bad Request'}, status=400)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def cart_item_view(request, item_id):
    user = get_user_from_request(request)
    if not user:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        item = CartItem.objects.get(id=item_id, cart__user=user)
    except CartItem.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)

    if request.method == 'PATCH':
        try:
            data = json.loads(request.body)
            count = int(data.get('count', item.count))
            if count < 1:
                return JsonResponse({'error': 'count must be >= 1'}, status=400)
            item.count = count
            item.save()
            return JsonResponse(_cart_items_response(user), safe=False)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({'error': 'Bad Request'}, status=400)

    if request.method == 'DELETE':
        item.delete()
        return JsonResponse(_cart_items_response(user), safe=False)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ── Interactions endpoint ─────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def interactions(request):
    user = get_user_from_request(request)
    if not user:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        event_type = data.get('event_type')
        if not product_id or event_type not in UserInteraction.INTERACTION_WEIGHTS:
            return JsonResponse({'error': 'product_id and valid event_type required'}, status=400)
        UserInteraction.objects.create(
            user=user,
            product_id=product_id,
            event_type=event_type,
            weight=UserInteraction.INTERACTION_WEIGHTS[event_type],
        )
        return HttpResponse(status=201)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Bad Request'}, status=400)


# ── Recommendations endpoint ──────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["GET"])
def recommendations(request):
    user = get_user_from_request(request)
    product_id = request.GET.get('product_id')
    limit = 6
    top_k_buffer = 12

    if user:
        cart_ids = list(
            CartItem.objects.filter(cart__user=user).values_list('product_id', flat=True)
        )
    else:
        raw = request.GET.get('cart_ids', '')
        cart_ids = [int(x) for x in raw.split(',') if x.strip().isdigit()]

    result_ids = []

    # Priority 1: personalized collaborative recommendations
    if user:
        result_ids = list(
            UserRecommendation.objects.filter(user=user, strategy='collaborative')
            .order_by('-score')
            .values_list('product_id', flat=True)[:top_k_buffer]
        )

    # Priority 2: aggregate content recommendations from cart items
    if not result_ids and cart_ids:
        from collections import defaultdict
        score_map = defaultdict(float)
        for cid in cart_ids:
            recs = ProductRecommendation.objects.filter(
                source_product_id=cid, strategy='content'
            ).order_by('-score')[:top_k_buffer]
            for rec in recs:
                if rec.target_product_id not in cart_ids:
                    score_map[rec.target_product_id] += rec.score
        result_ids = sorted(score_map, key=score_map.get, reverse=True)

    # Priority 3: content recs for specific product
    if not result_ids and product_id:
        result_ids = list(
            ProductRecommendation.objects.filter(
                source_product_id=product_id, strategy='content'
            ).order_by('-score').values_list('target_product_id', flat=True)[:top_k_buffer]
        )

    # Priority 4: fallback — content recs for first top-sale product
    if not result_ids and settings.TOP_SALE_IDS:
        result_ids = list(
            ProductRecommendation.objects.filter(
                source_product_id=settings.TOP_SALE_IDS[0], strategy='content'
            ).order_by('-score').values_list('target_product_id', flat=True)[:top_k_buffer]
        )

    if not result_ids:
        return JsonResponse([], safe=False)

    products = {
        p.id: p
        for p in Product.objects.filter(id__in=result_ids[:top_k_buffer]).prefetch_related('prices_set')
    }
    output = []
    for pid in result_ids:
        if pid in products:
            output.append(_product_response(products[pid]))
        if len(output) >= limit:
            break

    return JsonResponse(output, safe=False)
