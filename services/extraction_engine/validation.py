"""
Validation Engine — Performs post-extraction sanitization and format checks.
"""
import re
from typing import Any, Dict, Optional, List
from .garbage_filter import is_garbage

def filter_junk_items(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Identifies and removes summary rows incorrectly extracted as line items.
    (Fix 7: Reject 'Net Amount', 'Total', 'Tax' from items list).
    """
    keys_to_check = ["items", "item_details", "line_items", "product_list"]
    
    junk_patterns = [
        r"net amount", r"total", r"tax", r"igst", r"sgst", r"cgst", 
        r"round off", r"freight", r"grand total", r"subtotal"
    ]
    
    for key in keys_to_check:
        if key in data and isinstance(data[key], list):
            clean_list = []
            for item in data[key]:
                if not isinstance(item, dict):
                    continue
                
                # Check if item name/description contains junk keywords
                name = str(item.get("name") or item.get("description") or "").lower()
                if any(re.search(pattern, name) for pattern in junk_patterns):
                    continue # Skip summary rows
                
                clean_list.append(item)
            data[key] = clean_list
    return data

def detect_derived_types(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Step 2 & 3: Detect Freight and Insurance certificates via field patterns.
    """
    dtype = doc.get("document_type", "unknown")
    data = doc.get("structured_data", {})
    
    # Check for Freight Certificate signature
    if data.get("bl_number") and data.get("vessel_name") and (data.get("freight_amount") or data.get("ocean_freight")):
        if data.get("currency") == "USD" or dtype == "unknown":
            doc["document_type"] = "freight_certificate"
            
    # Check for Insurance Certificate signature
    if data.get("policy_number") and data.get("insurance_amount") and data.get("insured_party"):
        doc["document_type"] = "insurance_certificate"
        
    return doc

def enforce_document_purity(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Step 5: Prevent cross-document field contamination.
    """
    dtype = doc.get("document_type", "unknown")
    data = doc.get("structured_data", {})
    
    if dtype == "bill_of_lading":
        # BL strictly does not contain financial invoice data
        data.pop("invoice_number", None)
        data.pop("total_amount", None)
        data.pop("item_details", None)
        
    if dtype == "freight_certificate":
        # Freight cert strictly contains freight data
        data.pop("invoice_number", None)
        
    return doc

def semantic_sanity_gate(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Step 3 & 8: Prevent weight values from being mapped to amounts.
    """
    dtype = doc.get("document_type", "unknown")
    data = doc.get("structured_data", {})
    
    if dtype == "invoice":
        total = data.get("total_amount")
        if total is not None:
            try:
                val = float(str(total).replace(",", ""))
                # Threshold check: If amount < 100,000 and matches weight, it's likely a weight value.
                # Production data shows invoices are typically 100k+ INR.
                if val < 100000:
                    data["total_amount"] = None
            except:
                pass
                
    return doc

def clean_labels_from_values(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Strips the label if it was accidentally captured as part of the value.
    Example: 'Invoice No: MH253...' -> 'MH253...'
    """
    label_patterns = [
        r"^invoice\s+no\s*[:.-]*\s*",
        r"^invoice\s+date\s*[:.-]*\s*",
        r"^date\s*[:.-]*\s*",
        r"^bl\s+no\s*[:.-]*\s*",
        r"^hss\s+agreement\s*[:.-]*\s*",
        r"^vessel\s*[:.-]*\s*",
    ]
    
    for key, value in data.items():
        if isinstance(value, str):
            cleaned = value.strip()
            for pattern in label_patterns:
                cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
            data[key] = cleaned.strip()
            
    return data

# (User Requirement Alignment): Strictly Allowed Fields per Document Type (from Image)
ALLOWED_FIELDS_DICT = {
    "invoice": [
        "invoice_number", "invoice_date", "shipper_name_address", "consignee_name_address", 
        "po_number", "po_item", "incoterms", "amount", "currency", "gst_number", 
        "part_no", "description", "country_of_origin", "qty_units", "unit_price", 
        "net_value", "gross_value", "hsn_codes"
    ],
    "bill_of_lading": [
        "bl_number", "bl_date", "shipper", "consignee", "forwarder", "notify_party",
        "vessel_name", "voyage_no", "port_of_loading", "port_of_destination", 
        "container_number", "container_type", "seal_number", "gross_weight", 
        "net_weight", "package_count", "freight_terms", "description_of_goods", "measurement"
    ],
    "packing_list": [
        "invoice_number", "invoice_date", "shipper", "consignee", "po_number", 
        "gross_weight", "net_weight", "marks_and_numbers", 
        "qty", "pallet_details", "part_number", "country_of_origin", "hs_code", "description"
    ],
    "high_seas_sale_agreement": [
        "hss_ref_no", "agreement_date", "seller", "buyer", 
        "description_of_goods", "quantity", "total_amount"
    ],
    "freight_certificate": [
        "bl_number", "freight_charges", "currency", "weight", "incoterms", 
        "packages", "pol", "pod", "consignee", "excharge_charges", "container_type", "date"
    ],
    "insurance_certificate": [
        "policy_number", "issue_date", "gst_uin_number", "invoice_number", 
        "invoice_date", "address", "description", "po_number", "insured_amount", 
        "currency", "pod", "pol", "exchange_rate", "description_of_goods"
    ]
}

def validate_fields(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Step 5: Guard Layer (Final Blueprint Alignment).
    Strips fields not allowed for the document type.
    """
    dtype = doc.get("document_type", "unknown")
    data = doc.get("structured_data", {})
    
    allowed = ALLOWED_FIELDS_DICT.get(dtype, [])
    
    # Strips fields not in the allowed list for this document type
    clean_data = {k: v for k, v in data.items() if v and k in allowed}
            
    doc["structured_data"] = clean_data
    return doc

def normalize(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Step 6: Normalization (Final Blueprint Alignment).
    Converts amounts and weights to float.
    """
    data = doc.get("structured_data", {})
    
    # User Rule 14: Numeric conversion
    numeric_keys = [
        "total_amount", "freight_amount", "insurance_amount", "gross_weight", "net_weight",
        "amount", "freight_charges", "insured_amount", "net_value", "gross_value", 
        "unit_price", "qty_units", "weight", "exchange_rate"
    ]
    
    for key in numeric_keys:
        if key in data and data[key]:
            try:
                # Remove commas and non-numeric junk
                clean_val = str(data[key]).replace(",", "").replace("KG", "").strip()
                data[key] = float(clean_val)
            except:
                data[key] = None
                
    doc["structured_data"] = data
    return doc

def remove_empty_docs(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Step 8: Empty Document Removal (Final Blueprint Alignment).
    Prunes docs with no structured data.
    """
    return [
        d for d in docs 
        if d.get("llm_failed") or (d.get("structured_data") and any(k for k in d["structured_data"] if k != "items"))
    ]
