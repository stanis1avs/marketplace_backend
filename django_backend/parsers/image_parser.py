import json
from django_backend.constants import IMAGE_SEPARATORS

class ImageParser:
    def parse_images(self, picture_field: str) -> str:
        if not picture_field:
            return "[]"
        
        candidates = []
        for sep in IMAGE_SEPARATORS:
            if sep in picture_field:
                parts = [p.strip() for p in picture_field.split(sep) if p.strip()]
                candidates = parts
                break
        
        if not candidates:
            candidates = [picture_field.strip()]
        
        candidates = [c for c in candidates if c]
        
        return json.dumps(candidates, ensure_ascii=False)

image_parser = ImageParser()