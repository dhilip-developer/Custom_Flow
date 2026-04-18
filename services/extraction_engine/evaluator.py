"""
Evaluator Engine — Calculates extraction completeness and triggers LLM fallbacks.
"""
from typing import Dict, Any, Tuple

# Define expected fields for scoring
EXPECTED_FIELDS = {
    "invoice": [
        "invoice_number", "invoice_date", "buyer_name", "seller_name",
        "total_amount", "currency", "gst_number", "po_number", "po_date",
        "place_of_supply", "place_of_delivery", "items"
    ],
    "bill_of_lading": [
        "bl_number", "bl_date", "shipper", "consignee", "vessel_name",
        "voyage_no", "port_of_loading", "port_of_destination", "container_number",
        "seal_number", "gross_weight", "net_weight", "package_count"
    ],
    "packing_list": [
        "pl_number", "pl_date", "gross_weight",
        "net_weight", "marks_and_numbers", "product_details"
    ],
    "high_seas_sale_agreement": [
        "hss_ref_no", "agreement_date", "buyer", "seller", "bl_number",
        "vessel_name", "port_of_loading", "port_of_destination", "currency",
        "incoterms"
    ],
    "freight_certificate": [
        "bl_number", "vessel_name", "total_amount", "currency"
    ],
    "insurance_certificate": [
        "policy_number", "insured_party", "insured_amount", "currency",
        "invoice_number", "vessel_name", "description_of_goods"
    ],
    "certificate_of_origin": [
         "invoice_number", "country_of_origin", "product_name", "net_weight", "date"
    ]
}

# Critical fields that MUST be present to avoid fallback
CRITICAL_FIELDS = {
    "invoice": ["invoice_number", "total_amount", "buyer_name"],
    "bill_of_lading": ["bl_number", "vessel_name"],
    "packing_list": ["gross_weight", "net_weight"],
    "high_seas_sale_agreement": ["hss_ref_no", "bl_number"],
    "freight_certificate": ["bl_number"],
    "insurance_certificate": ["policy_number", "insured_amount"],
    "certificate_of_origin": ["country_of_origin"]
}


def evaluate_extraction(document_type: str, structured_data: Dict[str, Any]) -> Tuple[float, float]:
    """
    Computes completeness and critical scores.
    Returns (completeness_score, critical_score).
    """
    if not structured_data:
        return 0.0, 0.0

    dtype = document_type.lower()
    expected = EXPECTED_FIELDS.get(dtype, [])
    critical = CRITICAL_FIELDS.get(dtype, [])

    if not expected:
        # For support documents with no expected fields, consider them always structurally complete
        return 100.0, 100.0

    # Completeness Score
    non_null_fields = sum(1 for field in expected if structured_data.get(field))
    completeness_score = (non_null_fields / len(expected)) * 100

    # Critical Score
    if not critical:
        critical_score = 100.0
    else:
        critical_present = sum(1 for field in critical if structured_data.get(field))
        critical_score = (critical_present / len(critical)) * 100

    return completeness_score, critical_score


def should_trigger_fallback(
    document_type: str, 
    completeness_score: float, 
    critical_score: float, 
    structured_data: Dict[str, Any], 
    raw_text: str
) -> bool:
    """
    Decision Engine: Returns True if Gemini Fallback is required.
    """
    # 1. Unknown classification
    if document_type.lower() == "unknown":
        if len(raw_text.strip()) > 500:
            return True
        return False

    # 2. Support docs pass automatically
    if document_type.lower() not in CRITICAL_FIELDS:
        return False

    # 3. Empty structured data
    if not structured_data:
        return True

    # 4. Critical score missing
    if critical_score < 70.0:
        return True

    # 5. Completeness score too low
    if completeness_score < 80.0:
        return True

    # 6. Sparse data but lengthy text
    extracted_fields_count = len([k for k, v in structured_data.items() if v])
    if extracted_fields_count < 5 and len(raw_text.strip()) > 1000:
        return True

    return False
