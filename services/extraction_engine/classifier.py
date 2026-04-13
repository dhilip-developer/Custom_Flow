"""
Document Classifier — Pure regex classifier for document chunks.
Zero API calls, ~0.01ms per chunk.
"""
import re
from typing import Optional, Dict, List


# Title patterns checked against the first 10 lines (high confidence)
TITLE_PATTERNS: Dict[str, List[str]] = {
    "bill_of_lading": [
        r"BILL\s+OF\s+LADING",
        r"OCEAN\s+BILL",
        r"MASTER\s+BILL",
        r"HOUSE\s+BILL",
        r"SEA\s+WAYBILL",
        r"COMBINED\s+TRANSPORT\s+DOCUMENT",
    ],
    "invoice": [
        r"COMMERCIAL\s+INVOICE",
        r"TAX\s+INVOICE",
        r"PROFORMA\s+INVOICE",
        r"INVOICE\s*/\s*BILL\s+OF\s+SUPPLY",
    ],
    "packing_list": [
        r"PACKING\s+LIST",
        r"PACKING\s+SLIP",
        r"PACKING\s+NOTE",
        r"WEIGHT\s+LIST",
    ],
    "freight_certificate": [
        r"FREIGHT\s+CERTIFICATE",
        r"FREIGHT\s+MEMO",
        r"FREIGHT\s+INVOICE",
    ],
    "insurance_certificate": [
        r"INSURANCE\s+CERTIFICATE",
        r"CERTIFICATE\s+OF\s+INSURANCE",
        r"INSURANCE\s+POLICY",
        r"MARINE\s+(?:CARGO\s+)?INSURANCE",
    ],
    "high_seas_sale_agreement": [
        r"HIGH\s+SEA(?:S)?\s+SALE\s+AGREEMENT",
        r"HSS\s+AGREEMENT",
        r"HIGH\s+SEA(?:S)?\s+SALE",
    ],
    "certificate_of_origin": [
        r"CERTIFICATE\s+OF\s+ORIGIN",
    ],
}

# Keyword density scoring — used when title scan fails
KEYWORD_SCORES: Dict[str, List[str]] = {
    "bill_of_lading": [
        "shipper", "consignee", "vessel", "voyage", "port of loading",
        "port of discharge", "b/l", "container", "seal no", "on board",
        "freight prepaid", "freight collect", "notify party", "ocean vessel",
    ],
    "invoice": [
        "invoice no", "invoice date", "buyer", "seller", "total amount",
        "currency", "gst", "hsn", "po number", "unit price", "quantity",
        "tax", "igst", "cgst", "sgst", "place of supply",
    ],
    "packing_list": [
        "packing list", "gross weight", "net weight", "total packages",
        "marks and numbers", "pallet", "carton", "dimension",
        "cbm", "measurement",
    ],
    "freight_certificate": [
        "freight", "hbl no", "mbl no", "ocean freight", "freight amount",
        "freight charges", "local charges", "terminal handling",
    ],
    "insurance_certificate": [
        "insurance", "policy no", "insured", "premium", "sum insured",
        "perils", "voyage from", "voyage to", "claim",
    ],
    "high_seas_sale_agreement": [
        "high seas sale", "transferor", "transferee", "agreement",
        "foreign invoice", "incoterm", "hss ref", "sale on high seas",
    ],
}


def classify_chunk(text: str) -> str:
    """
    Classify a text chunk into a document type.
    Returns the document type string (e.g., 'invoice', 'bill_of_lading').
    Falls back to 'unknown' if no type can be determined.
    """
    if not text or not text.strip():
        return "unknown"

    # --- Phase 1: Title Scan (first 10 lines) ---
    lines = text.strip().split("\n")
    header_text = "\n".join(lines[:10]).upper()

    for doc_type, patterns in TITLE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, header_text, re.IGNORECASE):
                return doc_type

    # --- Phase 2: Full-text keyword density scoring ---
    text_lower = text.lower()
    scores: Dict[str, int] = {}

    for doc_type, keywords in KEYWORD_SCORES.items():
        score = 0
        for keyword in keywords:
            if keyword in text_lower:
                score += 1
        if score > 0:
            scores[doc_type] = score

    if scores:
        best = max(scores, key=scores.get)  # type: ignore
        # Require minimum 3 keyword hits for confidence
        if scores[best] >= 3:
            return best

    return "unknown"


def classify_all(chunks: List[str]) -> List[Dict[str, str]]:
    """
    Classify a list of text chunks.
    Returns list of dicts: [{"text": ..., "document_type": ...}]
    """
    results = []
    for chunk in chunks:
        doc_type = classify_chunk(chunk)
        results.append({
            "text": chunk,
            "document_type": doc_type,
        })
        print(f"[Classifier] → {doc_type} ({len(chunk)} chars)")
    return results
