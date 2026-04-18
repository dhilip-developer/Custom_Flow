"""
Normalization Module — Standardizes field values using robust logic.
"""
from typing import Any, Dict
from .normalizer import (
    normalize_number,
    normalize_weight,
    normalize_date,
    clean_whitespace
)

def normalize_all_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply standard normalization to all fields in the structured data.
    """
    if not data:
        return {}

    normalized = {}
    for key, value in data.items():
        if value is None:
            normalized[key] = None
            continue

        key_lower = key.lower()

        # 1. Date normalization
        if "date" in key_lower:
            normalized[key] = normalize_date(value)
            
        # 2. Weight normalization
        elif "weight" in key_lower:
            normalized[key] = normalize_weight(value)
            
        # 3. Numeric normalization (Amount, Quantity, etc.)
        elif any(k in key_lower for k in ["amount", "value", "quantity", "price", "rate"]):
            normalized[key] = normalize_number(value)
            
        # 4. Strings / Generic
        elif isinstance(value, str):
            normalized[key] = clean_whitespace(value)
            
        else:
            normalized[key] = value

    return normalized


def normalize_numbers(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compatibility wrapper for the user's requested modular structure.
    Specifically targets number casting.
    """
    for k, v in data.items():
        if isinstance(v, str):
            # Attempt to normalize common numeric fields
            if any(key in k.lower() for key in ["amount", "value", "quantity", "price", "weight"]):
                num = normalize_number(v)
                if num is not None:
                    data[k] = num
    return data
