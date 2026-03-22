# other_parse_helpers.py

from typing import Dict, List
from django_backend.constants import TRUE_AVAILABILITY_VALUES


def parse_params(param_string: str, default_value: str = "") -> Dict[str, List[str]]:
    result = {}
    
    if not param_string:
        return result

    items = param_string.split("|")

    for item in items:
        if ":" not in item:
            continue

        key, value = item.split(":", 1)

        key = key.strip()
        value = value.strip() or default_value

        if key not in result:
            result[key] = []

        result[key].append(value)

    return result


def parse_available(v: str | None) -> bool:
    if v is None:
        return False
    
    v = v.strip().lower()
    
    return v in TRUE_AVAILABILITY_VALUES