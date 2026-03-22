# feeds/tasks.py
import os
import hashlib
from django.conf import settings
from celery import shared_task
from django.utils import timezone
from api.models import FeedSource, RawFeedFile
from django_backend.adapters.admitad_feed_adapter import download_feed, parse_feed, upsert_product
import tempfile

@shared_task(bind=True, max_retries=3)
def fetch_and_import_feed(self, feed_source_id: int):
    """
    Основная задача: по FeedSource -> скачать фид -> сохранить метаданные -> распарсить и upsert
    """
    try:
        source = FeedSource.objects.get(pk=feed_source_id)
    except FeedSource.DoesNotExist:
        return {"error": "FeedSource not found"}

    feed_url = source.feed_url
    stream = None
    temp_path = None
    try:
        stream = download_feed(feed_url)
        try:
            
            tmp = tempfile.NamedTemporaryFile(delete=False)
            chunk = stream.read(1024 * 64)
            total = 0
            sha = hashlib.sha256()
            while chunk:
                b = chunk.encode('utf-8') if isinstance(chunk, str) else chunk
                sha.update(b)
                tmp.write(b)
                total += len(b)
                chunk = stream.read(1024 * 64)
            tmp.flush()
            tmp.close()
            temp_path = tmp.name
            sha_hex = sha.hexdigest()
            rf = RawFeedFile.objects.create(
                source=source,
                filename=os.path.basename(temp_path),
                sha256=sha_hex,
                size=total,
                local_path=temp_path
            )
            with open(temp_path, "r", encoding="utf-8", errors="ignore") as f:
                for item in parse_feed(f):
                    upsert_product(item, source=source)
        except Exception:
            raise
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * 5)
    finally:
        if stream:
            try:
                stream.close()
            except Exception:
                pass

    return {"status": "ok", "source": source.id}