import json
import re
from typing import Optional
from google import genai
from google.genai import types
from services.intelligence_utils import generate_gemini_content_with_retry


def _repair_json_string(s: str) -> str:
    """
    Attempt to fix the most common JSON copy-paste corruption:
    unescaped literal newlines / carriage returns / tabs inside string values.

    When users copy JSON from Swagger's pretty-printed response display,
    multi-line values (e.g. addresses) contain REAL newline characters instead
    of the escaped \\n — this breaks JSON.parse. We scan char-by-char and
    escape them only when we are inside a string literal.
    """
    result = []
    in_string = False
    escape_next = False

    for ch in s:
        if escape_next:
            result.append(ch)
            escape_next = False
            continue

        if ch == '\\' and in_string:
            result.append(ch)
            escape_next = True
            continue

        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue

        if in_string:
            if ch == '\n':
                result.append('\\n')
                continue
            elif ch == '\r':
                result.append('\\r')
                continue
            elif ch == '\t':
                result.append('\\t')
                continue

        result.append(ch)

    return ''.join(result)


def _safe_parse(raw: Optional[str], label: str) -> Optional[dict]:
    """
    Robustly parse a raw JSON string into a dict.
    Handles: BOM, surrounding whitespace, extra text around the JSON,
    smart/curly quotes, unescaped newlines inside values,
    and auto-unwraps Agent 3's 'extracted_data' wrapper.
    Returns None silently for empty/null inputs.
    """
    if raw is None:
        return None

    # Strip BOM (UTF-8 / UTF-16), zero-width chars, and all whitespace
    cleaned = raw.lstrip('\ufeff\u200b\u200c\u200d\ufffe').strip()

    if not cleaned or cleaned.lower() in ('null', 'none', '{}', '[]', '""', "''"):
        return None

    # Find the first '{' — user may have pasted extra text before the JSON
    brace_start = cleaned.find('{')
    if brace_start == -1:
        raise ValueError(
            f"No JSON object found in '{label}'. "
            f"Paste only the dictionary from Agent 3's 'extracted_data' field, "
            f"e.g. {{\"BILL NO.\": \"BL-001\", ...}}"
        )

    # Trim everything before the first '{'
    json_candidate = cleaned[brace_start:]

    # Normalize smart/curly quotes → straight quotes (common copy-paste issue)
    json_candidate = json_candidate.replace('\u201c', '"').replace('\u201d', '"')
    json_candidate = json_candidate.replace('\u2018', "'").replace('\u2019', "'")

    # First attempt: parse as-is
    try:
        parsed = json.loads(json_candidate)
    except json.JSONDecodeError:
        # Second attempt: repair unescaped newlines/tabs inside string values
        # (happens when copying from Swagger's pretty-printed response display)
        try:
            repaired = _repair_json_string(json_candidate)
            parsed = json.loads(repaired)
        except json.JSONDecodeError as e2:
            raise ValueError(
                f"Could not parse JSON for '{label}'. "
                f"The JSON appears malformed at character {e2.pos}. "
                f"Tip: copy directly from Agent 3's response box using the "
                f"'Download' button rather than selecting the text, to avoid "
                f"copy-paste formatting issues.\n"
                f"Detail: {e2}"
            )

    if not isinstance(parsed, dict):
        raise ValueError(
            f"Expected a JSON object ({{...}}) for '{label}', but got {type(parsed).__name__}."
        )

    # Empty dict — treat as not provided
    if not parsed:
        return None

    # Auto-unwrap Agent 3's extracted_data wrapper if present
    if "extracted_data" in parsed and isinstance(parsed["extracted_data"], dict) and len(parsed) == 1:
        inner = parsed["extracted_data"]
        return inner if inner else None

    return parsed


def cross_verify_documents(
    bill_of_lading: Optional[str],
    invoice: Optional[str],
    packing_list: Optional[str],
    freight_certificate: Optional[str],
    insurance_certificate: Optional[str],
) -> dict:
    """
    Agent 5: Cross-verifies field-level consistency across all submitted customs documents.
    Uses Gemini AI to semantically compare equivalent fields and produce a match/mismatch report
    including a full side-by-side comparison table.
    """
    client = genai.Client()

    # Parse each raw JSON string
    bol_data   = _safe_parse(bill_of_lading, "bill_of_lading")
    inv_data   = _safe_parse(invoice, "invoice")
    pl_data    = _safe_parse(packing_list, "packing_list")
    fc_data    = _safe_parse(freight_certificate, "freight_certificate")
    ins_data   = _safe_parse(insurance_certificate, "insurance_certificate")

    # Build documents provided list
    documents_provided = []
    doc_sections = []

    if bol_data:
        documents_provided.append("Bill of Lading (BOL)")
        doc_sections.append(f"--- BILL OF LADING (BOL) ---\n{json.dumps(bol_data, indent=2)}")

    if inv_data:
        documents_provided.append("Invoice")
        doc_sections.append(f"--- INVOICE ---\n{json.dumps(inv_data, indent=2)}")

    if pl_data:
        documents_provided.append("Packing List")
        doc_sections.append(f"--- PACKING LIST ---\n{json.dumps(pl_data, indent=2)}")

    if fc_data:
        documents_provided.append("Freight Certificate")
        doc_sections.append(f"--- FREIGHT CERTIFICATE ---\n{json.dumps(fc_data, indent=2)}")

    if ins_data:
        documents_provided.append("Insurance Certificate")
        doc_sections.append(f"--- INSURANCE CERTIFICATE ---\n{json.dumps(ins_data, indent=2)}")

    if len(documents_provided) < 2:
        return {
            "overall_verdict": "INSUFFICIENT DATA",
            "coherence_score": 0.0,
            "documents_provided": documents_provided,
            "summary": "At least 2 documents must be provided to perform cross-verification.",
            "comparison_table": [],
            "matched_fields": [],
            "mismatched_fields": [],
            "skipped_comparisons": []
        }

    documents_text = "\n\n".join(doc_sections)

    prompt = f"""
You are Agent 5: the Document Cross-Verification Agent for CustomsFlow, a customs clearance AI system.

You have been given the extracted JSON key-value data from the following customs documents:
{', '.join(documents_provided)}

YOUR TASK:
Perform a rigorous field-level cross-comparison across ALL provided documents to check whether they all belong to the same shipment. Compare semantically equivalent fields wherever the relevant documents are available.

═══════════════════════════════════════════════════════════════
CROSS-COMPARISON MATRIX — compare these pairs where applicable:
═══════════════════════════════════════════════════════════════

BOL ↔ Invoice:
  - BOL["HS CODE"] vs Invoice["HS CODE"]
  - BOL["DESCRIPTION OF GOODS"] vs Invoice["MATERIAL DESCRIPTION"]
  - BOL["CONSIGNEE/RECIEVER"] vs Invoice["SHIPPER NAME/CONSIGNEE NAME"] (consignee portion)

BOL ↔ Packing List:
  - BOL["GROSS WEIGHT"] vs Packing List["GROSS WEIGHT"]
  - BOL["PACKAGE"] vs Packing List["PACKAGE LIST"] (package count/type)

BOL ↔ Freight Certificate:
  - BOL["CONTAINER NUMBER"] vs Freight Certificate["CONTAINER NO."]
  - BOL["BILL NO."] vs Freight Certificate["HBL NO."]
  - BOL["GROSS WEIGHT"] vs Freight Certificate["WEIGHT"]
  - BOL["PACKAGE"] vs Freight Certificate["PACKAGES"]

Invoice ↔ Packing List:
  - Invoice["MATERIAL DESCRIPTION"] vs Packing List["MATERIAL DESCRIPTION"]
  - Invoice["QUANTITY"] vs Packing List["QUANTITY"]
  - Invoice["PART NUMBER"] vs Packing List["MATERIAL NUMBER"]

Invoice ↔ Insurance Certificate:
  - Invoice["INVOICE NUMBER AND DATE"] vs Insurance Certificate["INVOICE NUMBER"]
  - Invoice["TOTAL VALUE"] vs Insurance Certificate["INVOICE TOTAL VALUE"]
  - Invoice["PART NUMBER"] vs Insurance Certificate["PART NUMBER"]

Packing List ↔ Freight Certificate:
  - Packing List["GROSS WEIGHT"] vs Freight Certificate["WEIGHT"]
  - Packing List["PACKAGE LIST"] vs Freight Certificate["PACKAGES"]

═══════════════════════════════════════════════════════════════
SEMANTIC MATCHING RULES:
═══════════════════════════════════════════════════════════════
- Minor formatting differences are NOT mismatches: "1,500 KGS" == "1500 kg", "SHANGHAI PORT" == "Shanghai", "84713000" == "8471.30.00"
- Abbreviations are NOT mismatches: "M/S ABC CO." == "ABC Company"
- Empty/blank fields ("" or null): mark verdict as "UNVERIFIABLE" — do NOT count as mismatch
- Only flag MISMATCH when values are genuinely different (different numbers, names, IDs)
- If a field comparison is not applicable because a document wasn't provided, mark "N/A"

═══════════════════════════════════════════════════════════════
CRITICAL OUTPUT REQUIREMENT — COMPARISON TABLE:
═══════════════════════════════════════════════════════════════
You MUST output a "comparison_table" array. Each row in this table represents ONE field being tracked across ALL 5 documents (even if a document wasn't provided). Include EVERY field that appears in at least one provided document.

For each row, fill in the value from each document, or "—" if that document was not provided, or "N/A" if that document doesn't contain that field.

The verdict for each table row should be based on the cross-comparison matrix above:
- "MATCH" — all relevant documents agree
- "MISMATCH" — at least one relevant document disagrees
- "UNVERIFIABLE" — relevant documents have empty values
- "N/A" — this field is only in one document (no comparison possible)

═══════════════════════════════════════════════════════════════
COHERENCE SCORE:
═══════════════════════════════════════════════════════════════
Calculate as: (number of MATCH comparison pairs / total verifiable comparison pairs) * 100
Round to 1 decimal place.

VERDICT RULES:
- "COHERENT": zero MISMATCHes found across all comparisons
- "DISCREPANCIES FOUND": one or more genuine MISMATCHes

═══════════════════════════════════════════════════════════════
RETURN FORMAT — STRICT JSON ONLY, NO MARKDOWN:
═══════════════════════════════════════════════════════════════
{{
  "overall_verdict": "COHERENT" or "DISCREPANCIES FOUND",
  "coherence_score": float,
  "documents_provided": {json.dumps(documents_provided)},
  "summary": "One professional sentence summarising the finding.",
  "comparison_table": [
    {{
      "field_name": "HS CODE",
      "bill_of_lading": "84713000 or — or N/A",
      "invoice": "84713000 or — or N/A",
      "packing_list": "— or N/A",
      "freight_certificate": "— or N/A",
      "insurance_certificate": "— or N/A",
      "verdict": "MATCH",
      "discrepancy_note": null
    }}
  ],
  "matched_fields": [
    {{
      "field_name": "HS CODE — BOL vs Invoice",
      "documents_compared": ["Bill of Lading (BOL)", "Invoice"],
      "values": {{"Bill of Lading (BOL)": "84713000", "Invoice": "84713000"}},
      "status": "MATCH",
      "discrepancy_note": null
    }}
  ],
  "mismatched_fields": [
    {{
      "field_name": "GROSS WEIGHT — BOL vs Packing List",
      "documents_compared": ["Bill of Lading (BOL)", "Packing List"],
      "values": {{"Bill of Lading (BOL)": "1500 KG", "Packing List": "1450 KG"}},
      "status": "MISMATCH",
      "discrepancy_note": "Weight differs by 50 KG — BOL shows 1500 KG but Packing List shows 1450 KG."
    }}
  ],
  "skipped_comparisons": [
    {{
      "field_name": "INVOICE NUMBER — Invoice vs Insurance Certificate",
      "reason": "Insurance Certificate was not provided."
    }}
  ]
}}

═══════════════════════════════════════════════════════════════
DOCUMENT DATA TO COMPARE:
═══════════════════════════════════════════════════════════════
{documents_text}
"""

    try:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.0
        )

        response = generate_gemini_content_with_retry(
            client=client,
            model='gemini-2.5-flash',
            contents=[prompt],
            config=config
        )

        result = json.loads(response.text)

        # Always enforce documents_provided from our side
        result["documents_provided"] = documents_provided

        # Ensure comparison_table exists
        if "comparison_table" not in result:
            result["comparison_table"] = []

        return result

    except Exception as e:
        print(f"Error in Agent 5 cross-verification: {e}")
        return {
            "overall_verdict": "DISCREPANCIES FOUND",
            "coherence_score": 0.0,
            "documents_provided": documents_provided,
            "summary": f"Agent 5 encountered an error during cross-verification: {str(e)}",
            "comparison_table": [],
            "matched_fields": [],
            "mismatched_fields": [],
            "skipped_comparisons": []
        }
