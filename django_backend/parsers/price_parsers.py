# parsers/price_parsers.py
from decimal import Decimal, InvalidOperation
from django_backend.constants import CURRENCY_MAP


class PriceParser:
    
    def normalize_price(self, price_raw: str) -> Decimal | None:
        if not price_raw:
            return None
        
        try:
            p = price_raw.strip().replace("\xa0", "").replace(" ", "").replace(",", ".")
            if "-" in p:
                p = p.split("-")[0]
            return Decimal(p)
        except (InvalidOperation, ValueError):
            return None
    
    def extract_currency(self, price_raw: str) -> str:
        if not price_raw:
            return ""
        
        price_lower = price_raw.lower()
        
        for symbol, code in CURRENCY_MAP.items():
            if symbol in price_lower:
                return code
        
        return ""

price_parser = PriceParser()
