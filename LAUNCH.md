# Django Backend for Marketplace

This is a Django REST API backend for the marketplace application, converted from Node.js/Koa to Python/Django.

## Setup

1. Install dependencies:
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your database configuration
```

3. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

4. Create superuser (optional):
```bash
python manage.py createsuperuser
```

5. Run the development server:
```bash
python manage.py runserver
```

6. Run the Celery worker:
```bash
celery -A django_backend worker -l info -P solo
```

7. Run the task to parse
```bash
python manage.py shell
from django_backend.feeds.tasks import fetch_and_import_feed
from api.models import FeedSource                 
feed = FeedSource.objects.get(name="fable")
fetch_and_import_feed.delay(feed.id)
```

## API Endpoints

- `GET /api/top-sales/` - Get top sale products
- `GET /api/categories/` - Get all categories
- `GET /api/items/` - Search products with pagination
- `GET /api/items/<id>/` - Get product details with sizes
- `POST /api/order/` - Process order

## Database Models

- **Category**: Product categories
- **Product**: Products with title, price, images, etc.
- **Size**: Product sizes and availability

The backend uses Django ORM with PostgreSQL database.
