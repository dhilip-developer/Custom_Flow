"""
Document Classifier — Pure regex classifier for document chunks.
Zero API calls, ~0.01ms per chunk.

Supports: Invoice, BOL, Packing List, Weight Note, Freight Cert,
Insurance Cert, HSS Agreement, CoO, CoA, IEC, GST Cert,
Letter of Authority, HSS Cover/Customs/Shipping Letters.
"""
import re
from typing import Optional, Dict, List


# ── Title patterns checked against first 15 lines (high confidence) ──
# ORDER MATTERS: terms_and_conditions is checked before invoice to prevent
# General Conditions / T&C pages from being misclassified as invoices.
TITLE_PATTERNS: Dict[str, List[str]] = {
    "terms_and_conditions": [
        r"General\s+(?:Conditions|Terms)\s+(?:of\s+)?Sale",
        r"General\s+Terms\s+and\s+Conditions",
        r"Terms\s+(?:and|&)\s+Conditions",
        r"Conditions\s+of\s+Sale\s+and\s+Delivery",
    ],
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
        r"(?:^|\n)\s*INVOICE\s*(?:\n|$)",
    ],
    "packing_list": [
        r"PACKING\s+LIST",
        r"PACKING\s+SLIP",
        r"PACKING\s+NOTE",
    ],
    "weight_note": [
        r"WEIGHT\s+NOTE",
        r"WEIGHT\s+LIST",
        r"WEIGHT\s+MEMO",
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
    ],
    "certificate_of_origin": [
        r"CERTIFI\w*\s+O[Ff]\s+ORIGIN",
    ],
    "certificate_of_analysis": [
        r"CERTIFI\w*\s+O[Ff]\s+ANALYSIS",
    ],
    "iec_certificate": [
        r"IMPORTER[\s-]*EXPORTER\s+CODE",
        r"\bIEC\b.*CERTIF",
    ],
    "gst_certificate": [
        r"REGISTRATION\s+CERTIFICATE",
        r"Form\s+GST\s+REG",
        r"GST\s+REG[\s-]*0[0-9]",
    ],
    "letter_of_authority": [
        r"LETTER\s+OF\s+AUTHORITY",
        r"POWER\s+OF\s+ATTORNEY",
    ],
    "hss_cover_letter": [
        r"Sub:?\s*(?:Sub:?)?\s*Sale\s+of\s+Goods\s+on\s+High\s+Sea",
        r"Ref:\s*HSS/",
    ],
    "customs_letter": [
        r"ASST\.?/DY\.?\s+COMMISSIONER\s+OF\s+CUSTOMS",
        r"COMMISSIONER\s+OF\s+CUSTOMS",
    ],
    "shipping_letter": [
        r"OCEAN\s+NETWORK\s+EXPRESS\s+LINE",
    ],
}

# ── T&C / Legal boilerplate detection keywords ──
# If a chunk contains 5+ of these, it's almost certainly T&C, not a real document.
TC_KEYWORDS = [
    "force majeure", "limitation of liability", "notification of defects",
    "replacement of goods", "indemnity", "termination", "warranties and representations",
    "applicable law", "jurisdiction", "governing law", "breach of contract",
    "arbitration", "compliance", "foreign trade law", "technical advice",
    "trademarks", "retention of title", "seller's specifications",
    "general conditions", "dispute resolution", "accrued rights",
    "shall not be liable", "without prejudice", "fiduciary capacity",
]

# ── Keyword density scoring — used when title scan fails ──
KEYWORD_SCORES: Dict[str, List[str]] = {
    "bill_of_lading": [
        "shipper", "consignee", "vessel", "voyage", "port of loading",
        "port of discharge", "b/l", "container", "seal no", "on board",
        "freight prepaid", "freight collect", "notify party", "ocean vessel",
        "carrier", "laden on board",
    ],
    "invoice": [
        "invoice no", "invoice date", "buyer", "seller", "total amount",
        "currency", "gst", "hsn", "po number", "unit price", "quantity",
        "tax", "igst", "cgst", "sgst", "place of supply", "assessable value",
        "payment due date",
    ],
    "packing_list": [
        "packing list", "gross weight", "net weight", "total packages",
        "marks and numbers", "pallet", "carton", "dimension",
        "cbm", "measurement",
    ],
    "weight_note": [
        "weight note", "gross", "net", "tare", "batch no",
        "country of origin", "delivery number",
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
        "annexure", "hss agreement ref",
    ],
    "certificate_of_origin": [
        "origin", "country of origin", "certify", "shipped", "made in",
    ],
    "certificate_of_analysis": [
        "certificate of analysis", "inspection", "specification",
        "batch", "result", "method", "viscosity",
    ],
}


def _is_terms_and_conditions(text: str) -> bool:
    """
    Detect if text is legal boilerplate / Terms & Conditions.
    Returns True if 5+ T&C-specific phrases are found.
    """
    text_lower = text.lower()
    hits = sum(1 for kw in TC_KEYWORDS if kw in text_lower)
    return hits >= 5


def classify_chunk(text: str) -> str:
    """
    Classify a text chunk into a document type.
    Returns the document type string (e.g., 'invoice', 'bill_of_lading').
    Falls back to 'unknown' if no type can be determined.
    """
    if not text or not text.strip():
        return "unknown"

    # --- Phase 0: T&C / Legal boilerplate check (highest priority) ---
    # This MUST run before title scan because T&C pages contain words like
    # "Invoice", "Buyer", "Seller" which fool the invoice classifier.
    if _is_terms_and_conditions(text):
        return "terms_and_conditions"

    # --- Phase 1: Title Scan (first 15 lines) ---
    lines = text.strip().split("\n")
    header_text = "\n".join(lines[:15])

    for doc_type, patterns in TITLE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, header_text, re.IGNORECASE | re.MULTILINE):
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
