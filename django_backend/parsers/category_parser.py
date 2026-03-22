# parsers/category_parser.py
from typing import Tuple
from django_backend.constants import CATEGORY_KEYWORDS, DEFAULT_CATEGORY, DEFAULT_MAX_WORDS
from api.models import Category

class CategoryParser:
    def __init__(self):
        self.category_keywords = CATEGORY_KEYWORDS
        self.default_category = DEFAULT_CATEGORY
        self.default_max_words = DEFAULT_MAX_WORDS
    
    def normalize_category_name(self, category_str: str) -> str:
        if not category_str:
            return ""
        
        normalized = category_str.strip().lower()
        
        while "  " in normalized:
            normalized = normalized.replace("  ", " ")
        
        return normalized
    
    def extract_first_words(self, title: str, max_words: int = None) -> str:
        if not title:
            return ""
        
        max_words = max_words or self.default_max_words
        words = title.strip().split()[:max_words]
        return " ".join(words).title()
    
    def detect_category_from_title(self, title: str) -> str:
        if not title:
            return self.default_category
        
        title_lower = title.lower()
        
        for category, data in self.category_keywords.items():
            if any(keyword in title_lower for keyword in data['keywords']):
                return category
        
        return self.default_category
    
    def parse_category_string(self, category_str: str) -> Tuple[str, str]:        
        normalized = self.normalize_category_name(category_str)
        
        parts = [part.strip() for part in normalized.replace("/", " ").replace("\\", " ").split() if part.strip()]
        
        detected_category = None
        category_name = category_str
        
        for part in parts:
            for category, data in self.category_keywords.items():
                if any(keyword in part for keyword in data['keywords']):
                    detected_category = category
                    gender = self._detect_gender(parts, data['gender_keywords'])
                    
                    if gender:
                        category_name = f"{gender} {category}"
                    else:
                        category_name = category
                    return detected_category, category_name
        
        return self.default_category, category_str
    
    def _detect_gender(self, parts: list, gender_keywords: list) -> str:
        for gender_word in gender_keywords:
            if any(gender_word.lower() in p.lower() for p in parts):
                return gender_word.title()
        return ""
    
    def pase_title_string(self, title: str, category_str: str = "") -> Tuple[str, str]:
        detected = self.detect_category_from_title(title)
        if detected != self.default_category:
            if category_str:
                return detected, f"{detected} ({category_str})"
            return detected, self.extract_first_words(title, 1)
        return self.default_category, self.extract_first_words(title, 1)
    
    def smart_category_detection(self, category_str: str, title: str = "") -> Tuple[str, str]:
        if category_str:
            detected_category, category_name = self.parse_category_string(category_str)    
        if title:
            detected_category, category_name = self.pase_title_string(title, category_str)
        
        return detected_category, category_name
    
    def get_or_create_category(self, category_str: str, title: str = "") -> Category:
        detected_category, category_name = self.smart_category_detection(category_str, title)
        existing_cats = Category.objects.filter(title=detected_category)
        if existing_cats.exists():
            return existing_cats.first()
    
        cat = Category.objects.create(
            title=detected_category,
            parsed_category=category_name
        )
        
        return cat


category_parser = CategoryParser()
