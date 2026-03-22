import os
import django
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_backend.settings")

django.setup()

app = Celery("django_backend")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()