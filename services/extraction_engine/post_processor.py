"""
Post Processor Engine — Handles merging, normalization, and classification correction.
"""
from typing import List, Dict, Any
import copy
import re

from models.schemas import SuperExtractionResult
from services.extraction_engine.normalizer import normalize_number

def normalize_data(structured_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizes deeply nested data explicitly enforcing numeric conversions where applicable.
    """
    norm_data = copy.deepcopy(structured_data)
    
    # Common numeric fields
    numeric_fields = [
        "total_amount", "gross_weight", "net_weight", "package_count",
        "foreign_invoice_amount", "quantity", 
        "unit_price", "total_price"
    ]
    
    def _clean_dict(d: dict):
        for k, v in d.items():
            if isinstance(v, dict):
                _clean_dict(v)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        _clean_dict(item)
            elif v is not None and any(num_key in k.lower() for num_key in numeric_fields):
                # Ensure numbers are converted to int/float and stripped of units
                if isinstance(v, str):
                    val = normalize_number(v)
                    if val is not None:
                        d[k] = val
                    
    _clean_dict(norm_data)
    return norm_data

def fix_document_type(document: SuperExtractionResult) -> SuperExtractionResult:
    """
    Classification Correction rules.
    """
    dtype = document.document_type.lower()
    data = document.structured_data
    
    # Rule 0: Drop T&C / boilerplate documents entirely
    if dtype == "terms_and_conditions":
        return document  # Will be filtered in merge_documents
    
    # Rule 1: Freight Certificate check — ONLY for unknown/unclassified docs
    # that have freight-specific indicators (not just USD + BL which invoices also have)
    if dtype in ("unknown", "additional documents"):
        if data.get("currency") == "USD" and data.get("bl_number"):
            has_freight_fields = (
                data.get("freight_amount") or data.get("ocean_freight") or
                data.get("local_charges") or data.get("terminal_handling")
            )
            if has_freight_fields:
                document.document_type = "freight_certificate"
                return document
        
    # Rule 2: Packing List check
    # if it's currently incorrectly classified and has weights
    if dtype in ("unknown", "additional documents"):
        if data.get("gross_weight") or data.get("net_weight"):
            if not data.get("total_amount") and not data.get("invoice_number"):
                document.document_type = "packing_list"
                return document
                
    # Rule 3: Bill of Lading check
    if dtype in ("unknown", "additional documents"):
        if data.get("bl_number") and data.get("vessel_name") and data.get("port_of_loading"):
            if not data.get("freight_amount") and not data.get("hss_ref_no"):
                document.document_type = "bill_of_lading"
                return document
                
    return document

# Document types that should be silently dropped from output
SKIPPED_TYPES = {"terms_and_conditions", "unknown"}


def _is_junk_invoice(data: dict) -> bool:
    """
    Detect an invoice that is actually T&C/legal text.
    Symptoms: many items with null names or sentence-length names and no prices.
    """
    items = data.get("items", [])
    if not items or len(items) < 10:
        return False
    
    junk_count = 0
    for item in items:
        name = item.get("name") or ""
        has_qty = item.get("quantity") is not None
        has_price = item.get("unit_price") is not None or item.get("total_price") is not None
        # Sentence-length names with no real data = OCR'd legal text
        if (not name or len(name) > 60) and not has_qty and not has_price:
            junk_count += 1
    
    return junk_count > len(items) * 0.6  # 60%+ junk items = not a real invoice


def merge_documents(documents: List[SuperExtractionResult]) -> List[SuperExtractionResult]:
    """
    Merge documents of the same type or identifiers.
    Rules:
    - Filter out T&C and junk documents
    - Same invoice_number → merge
    - Same bl_number → merge
    - Same weights + packages → merge packing lists
    - BOL: also merge on vessel_name or container_number when bl_number is missing
    """
    if not documents:
        return []
        
    merged_map: Dict[str, SuperExtractionResult] = {}
    
    for doc in documents:
        # First fix classification
        doc = fix_document_type(doc)
        
        dtype = doc.document_type.lower()
        data = doc.structured_data
        
        # Drop T&C and unknown documents
        if dtype in SKIPPED_TYPES:
            print(f"[PostProcessor] Dropping {dtype} document (not a customs document)")
            continue
            
        # Drop junk invoices (T&C text misclassified as invoice items)
        if dtype == "invoice" and _is_junk_invoice(data):
            print(f"[PostProcessor] Dropping junk invoice ({len(data.get('items', []))} noise items)")
            continue
        
        doc.structured_data = normalize_data(doc.structured_data)
        data = doc.structured_data  # re-bind after normalization
        
        # Build merge identifier logic
        doc_id = str(
            data.get("invoice_number") or 
            data.get("bl_number") or 
            data.get("hss_ref_no") or 
            data.get("pl_number") or ""
        ).strip().upper()
        
        # BOL-specific merge: if no bl_number, try vessel_name or container_number
        if not doc_id and dtype == "bill_of_lading":
            vessel = str(data.get("vessel_name", "")).strip().upper()
            container = str(data.get("container_number", "")).strip().upper()
            if vessel:
                doc_id = f"VESSEL-{vessel}"
            elif container:
                doc_id = f"CNTR-{container}"
        
        if not doc_id and dtype == "packing_list":
            gw = str(data.get("gross_weight", "")).strip()
            doc_id = f"PL-{gw}"

        # If no strict identifier exists, isolate it with a unique ID
        if not doc_id:
            doc_id = str(id(doc))
            
        key = f"{dtype}::{doc_id}"
        
        if key not in merged_map:
            merged_map[key] = doc
        else:
            base = merged_map[key].structured_data
            for field, value in data.items():
                if not value:
                    continue
                if not base.get(field):
                    base[field] = value
                elif field in ("items", "product_details") and isinstance(value, list):
                    existing = base.get(field, [])
                    # Append items checking for strict duplicates
                    for new_item in value:
                        if new_item not in existing:
                            existing.append(new_item)
                    base[field] = existing
                elif isinstance(value, str) and len(str(value)) > len(str(base.get(field, ""))):
                    # Replace with longer (assumed better extracted) string
                    base[field] = value

    return list(merged_map.values())
