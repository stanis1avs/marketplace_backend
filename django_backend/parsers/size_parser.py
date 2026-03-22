from django_backend.constants import SIZE_KEYWORDS, SIZE_MAPPING

class SizeParser:
    def parse_sizes_from_param(self, param_field: str) -> list[str]:
        if not param_field:
            return []
        
        s = param_field.lower()
        sizes = []
        
        if "размер" in s or "size" in s:
            tokens = [t.strip(",:;()[]") for t in param_field.replace("\n", " ").split() if t.strip()]
            for t in tokens:
                tt = t.strip().lower()
                if any(ch.isdigit() for ch in tt) or tt in SIZE_KEYWORDS:
                    sizes.append(t)
        
        return sizes
    
    def normalize_size(self, size: str) -> str:
        if not size:
            return ""
        
        size = size.strip().upper()
        
        return SIZE_MAPPING.get(size, size)
    

size_parser = SizeParser()