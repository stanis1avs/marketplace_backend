# adapters/admitad_feed_adapter.py
import csv
import io
from decimal import Decimal
from typing import Iterator, Dict, Any, IO
import requests
import gzip
from django.db import transaction
from api.models import Product, Category, Size, FeedSource, Prices
from django_backend.parsers.category_parser import category_parser
from django_backend.parsers.price_parsers import price_parser
from django_backend.parsers.image_parser import image_parser
from django_backend.parsers.size_parser import size_parser
from django_backend.parsers.other_parse_helpers import parse_params, parse_available

# ------ download_feed -----------------------------------------------------------------

def download_feed(url):
    resp = requests.get(url, stream=True)
    resp.raise_for_status()

    content_encoding = resp.headers.get("Content-Encoding", "")

    raw = resp.content

    if "gzip" in content_encoding or url.endswith(".gz"):
        raw = gzip.decompress(raw)

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("cp1251")

    return io.StringIO(text)


# ------ parse_feed (streaming CSV parsing) --------------------------------------------
def parse_feed(stream: IO[str]) -> Iterator[Dict[str, Any]]:
    try:
        stream.seek(0)
    except Exception:
        pass

    reader = csv.DictReader(stream, delimiter=';', skipinitialspace=True)
    for row in reader:
        prod_id = row.get('id') or row.get('ID') or row.get('Id')

        title = row.get('name') or row.get('title') or row.get('model') or ''
        vendor = row.get('vendor') or row.get('manufacturer') or ''
        sku = row.get('vendorCode') or row.get('vendor_code') or ''
        price_raw = row.get('price') or row.get('oldprice') or ''
        price = price_parser.normalize_price(price_raw) or Decimal("0.00")
        currency = price_parser.extract_currency(row.get('currencyId') or '') or ''
        picture = row.get('picture') or ''
        images_json = image_parser.parse_images(picture)
        category_raw = row.get('categoryId') or ''

        available = parse_available(row.get('available') or row.get('count') or '')

        params = parse_params(row["param"], "")

        item = {
            "source_product_id": prod_id,
            "title": title.strip(),
            "sku": sku.strip(),
            "manufacturer": vendor.strip(),
            "price": price,
            "currency": currency,
            "available": available,
            "images": images_json,
            "category_raw": category_raw,
            "params": params,
            "raw_row": row,
            "url": row.get('url') or '',
            "description": row.get('description') or '',
            "modified_time": row.get('modified_time') or row.get('modified') or '',
        }
        yield item


# ------ DB upsert ----------------------------------------------------------------------------
@transaction.atomic
def upsert_product(item: Dict[str, Any], source: FeedSource | None = None) -> Product:
    cat = None
    category_raw = item.get("category_raw", "")
    title = item.get("title", "")
    
    if category_raw or title:
        cat = category_parser.get_or_create_category(category_raw, title)
    
    if cat is None:
        cat = Category.objects.create(
            title="Разное",
            parsed_category="error"
        )

    prod_defaults = {
        'source_product_id': item['source_product_id'],
        'source': source,
        'title': item['title'][:255],
        'sku': str(item.get('sku') or '')[:255],
        'manufacturer': (item.get('manufacturer') or '')[:255],
        'color': item.get("params", {}).get("Цвет", "")[0] if item.get("params", {}).get("Цвет", "") else None,
        'material': None,
        'season': None,
        'reason': None,
        'images': item.get('images') or "[]",
        'category': cat,
    }

    product_obj, created = Product.objects.update_or_create(
        source_product_id=item['source_product_id'],
        defaults=prod_defaults
    )

    try:
        currency = item.get('currency') or 'RUB'
        price = item['price'] or Decimal('0.00')
        old_price = item.get('old_price') or Decimal('0.00')
        max_price = max(price, old_price)
        min_price = min(price, old_price)
        Prices.objects.update_or_create(product=product_obj, price=price, currency=currency, max_price=max_price, min_price=min_price)
    except Exception:
        pass
    

    sizes = item.get("params", {}).get("Размер", [])

    for size in sizes:
        Size.objects.update_or_create(
            product=product_obj,
            size=size_parser.normalize_size(size),
            defaults={'available': item.get('available', True)}
        )

    return product_obj      