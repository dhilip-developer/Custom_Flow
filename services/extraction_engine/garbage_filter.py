"""
Garbage Filter — Identifies noise and labels incorrectly extracted as data.
"""

INVALID_VALUES = [
    "B/L Date", "Buyer PO Date", "Port of Loading",
    ").", "which expression shall", "Authorised Signatory",
    "Packing List", "Invoice No", "Date:", "Total Amount",
    "HSS Agreement Ref", "Agreement Date", "Vessel Name",
    "Port of Destination", "Page No", "Page:", "No.",
    "Place of Receipt", "Place of Delivery", "Final Destination"
]

def is_garbage(value: str) -> bool:
    """
    Returns True if the value appears to be OCR noise, a field label,
    or common legal boilerplate.
    """
    if not value or not isinstance(value, str):
        return True
    
    val_clean = value.strip()
    
    # Empty or single character
    if len(val_clean) < 2:
        return True
        
    # Exact label matches
    if val_clean in INVALID_VALUES:
        return True
        
    # Common boilerplate indicators
    boilerplate_indicators = [
        ").", "shall", "whereof", "hereby", "undersigned", 
        "authorised", "signatory", "stamp", "seal"
    ]
    val_lower = val_clean.lower()
    if any(indicator in val_lower for indicator in boilerplate_indicators):
        # We allow "shall" only if it's a very long sentence (likely a product desc), 
        # but usually it's noise in customs fields.
        if len(val_clean) < 100:
            return True
            
    return False
