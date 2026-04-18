"""
Document Splitter — Splits merged raw text from Agent 1 into individual document chunks.
Uses delimiter detection + keyword boundary scanning.

Agent 1 inserts '===' delimiters between each page's text. This splitter:
1. Splits on those delimiters first (one chunk per page)
2. Then merges adjacent chunks that belong to the same logical document
3. Drops junk chunks (T&C, legal boilerplate, stamp papers, PAN cards)
"""
import re
from typing import List, Dict, Tuple, Optional


# ── Document title patterns (checked in first 15 lines of a chunk) ──
DOCUMENT_TITLES: Dict[str, List[str]] = {
    "invoice": [
        r"COMMERCIAL\s+INVOICE",
        r"TAX\s+INVOICE",
        r"PROFORMA\s+INVOICE",
        r"INVOICE\s*/\s*BILL\s+OF\s+SUPPLY",
        r"(?:^|\n)\s*INVOICE\s*$",
    ],
    "bill_of_lading": [
        r"BILL\s+OF\s+LADING",
        r"OCEAN\s+BILL",
        r"MASTER\s+BILL",
        r"HOUSE\s+BILL",
        r"SEA\s+WAYBILL",
        r"COMBINED\s+TRANSPORT\s+DOCUMENT",
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
        r"CERTIFI\w*\s+OF\s+ORIGIN",
    ],
    "certificate_of_analysis": [
        r"CERTIFI\w*\s+OF\s+ANALYSIS",
    ],
    "iec_certificate": [
        r"IMPORTER[\s-]*EXPORTER\s+CODE",
        r"\bIEC\b.*CERTIF",
    ],
    "gst_certificate": [
        r"REGISTRATION\s+CERTIFICATE",
        r"GST\s+REG",
        r"Form\s+GST\s+REG",
    ],
    "letter_of_authority": [
        r"LETTER\s+OF\s+AUTHORITY",
        r"POWER\s+OF\s+ATTORNEY",
    ],
    "hss_cover_letter": [
        r"Sub:?\s*(?:Sub:?)?\s*Sale\s+of\s+Goods\s+on\s+High\s+Sea",
        r"HIGH\s+SEA\s+SALE\s+INVOICE",
        r"Ref:\s*HSS/",
    ],
    "customs_letter": [
        r"ASST\.?/DY\.?\s+COMMISSIONER\s+OF\s+CUSTOMS",
        r"COMMISSIONER\s+OF\s+CUSTOMS",
    ],
    "shipping_letter": [
        r"OCEAN\s+NETWORK\s+EXPRESS",
        r"(?:To,?\s*\n.*(?:SHIPPING|LINE|EXPRESS|MAERSK|MSC|CMA|HAPAG))",
    ],
}

# ── Junk patterns — skip these entirely ──
JUNK_PATTERNS = [
    r"General\s+Conditions?\s+of\s+Sale",
    r"These\s+General\s+Conditions",
    r"Quotations\s+and\s+Orders",
    r"Limitation\s+of\s+Liability",
    r"Force\s+Majeure",
    r"Applicable\s+Law.*Interpretation",
    r"Foreign\s+Trade\s+Law\s+Requirements",
    r"Compliance.*anti-bribery",
    r"Termination.*solvency",
    r"Revised:?\s*April\s+20\d{2}",
    r"Original\s+for\s+Recipient.*Transporter.*Supplier",
    r"Annexure[\s-]*3",  # GCS annexure
    r"^\s*I+\.\s+General\s*$",  # Section headers like "I. General"
]

# ── PAN card / stamp paper patterns ──
NOISE_DOC_PATTERNS = [
    r"आयकर\s+विभाग",  # Hindi Income Tax
    r"INCOME\s+TAX\s+DEPARTMENT",
    r"PAN\s+CARD",
    r"Permanent\s+Account\s+Number",
    r"भारतीय\s+गैर\s+न्यायिक",  # Indian non-judicial stamp
    r"NON[\s-]*JUDICIAL",
    r"STAMP\s+PAPER",
]


def _detect_type(text: str) -> Optional[str]:
    """Check first 15 lines for a document title match."""
    lines = text.strip().split("\n")
    header = "\n".join(lines[:15])

    for doc_type, patterns in DOCUMENT_TITLES.items():
        for pattern in patterns:
            if re.search(pattern, header, re.IGNORECASE | re.MULTILINE):
                return doc_type
    return None


def _is_junk(text: str) -> bool:
    """Check if the chunk is legal boilerplate, T&C, or stamp paper."""
    # Short chunks can't be junk
    if len(text) < 200:
        return False

    header = "\n".join(text.strip().split("\n")[:10])
    for pattern in JUNK_PATTERNS:
        if re.search(pattern, header, re.IGNORECASE):
            return True

    # Full-text check for noise docs
    for pattern in NOISE_DOC_PATTERNS:
        if re.search(pattern, text[:500], re.IGNORECASE):
            return True

    # Heuristic: if >80% of lines are long prose (>100 chars), it's likely T&C
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if len(lines) > 20:
        long_lines = sum(1 for l in lines if len(l) > 100)
        if long_lines / len(lines) > 0.6:
            return True

    return False


def _is_noise_doc(text: str) -> bool:
    """PAN cards, stamp papers, and other identity docs with no extractable data."""
    for pattern in NOISE_DOC_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def split_raw_text(raw_text: str) -> List[str]:
    """
    Split merged raw text from Agent 1 into individual document chunks.

    Pipeline:
        1. Split on '===' delimiters (Agent 1 inserts these between pages)
        2. Classify each page-chunk by title
        3. Merge adjacent pages of same type
        4. Drop junk (T&C, legal, stamp papers)
    """
    if not raw_text or not raw_text.strip():
        return []

    # --- Step 1: Split by Agent 1's === delimiter ---
    delimiter_pattern = r"\n\s*={10,}\s*\n"
    page_chunks = re.split(delimiter_pattern, raw_text)
    page_chunks = [s.strip() for s in page_chunks if s.strip() and len(s.strip()) > 30]

    if not page_chunks:
        return []

    print(f"[Splitter] Delimiter split: {len(page_chunks)} raw page chunks")

    # If only 1 chunk (no delimiters found), try keyword splitting
    if len(page_chunks) == 1:
        page_chunks = _split_by_keywords(page_chunks[0])
        if len(page_chunks) <= 1:
            print(f"[Splitter] Single chunk, no boundaries found")
            return page_chunks

    # --- Step 2: Classify each page chunk ---
    classified: List[Dict] = []
    for i, chunk in enumerate(page_chunks):
        doc_type = _detect_type(chunk)
        is_junk = _is_junk(chunk)
        is_noise = _is_noise_doc(chunk)

        if is_junk:
            print(f"[Splitter] Page {i+1}: SKIP (legal/T&C, {len(chunk)} chars)")
            continue
        if is_noise:
            print(f"[Splitter] Page {i+1}: SKIP (noise doc, {len(chunk)} chars)")
            continue

        if doc_type:
            print(f"[Splitter] Page {i+1}: {doc_type} ({len(chunk)} chars)")
        else:
            # No title found — check if it's a continuation of previous doc
            if classified:
                prev = classified[-1]
                # If previous doc is a known type and this unknown chunk is small-ish,
                # merge it as continuation
                if prev["type"] and len(chunk) < 2000:
                    print(f"[Splitter] Page {i+1}: continuation of {prev['type']} ({len(chunk)} chars)")
                    prev["text"] += "\n" + chunk
                    continue

            print(f"[Splitter] Page {i+1}: unknown ({len(chunk)} chars)")

        classified.append({"type": doc_type, "text": chunk})

    # --- Step 3: Merge adjacent chunks of same type ---
    merged: List[Dict] = []
    for item in classified:
        doc_type = item["type"]
        
        if not doc_type:
            # Unknown type — keep as separate chunk
            merged.append(item)
            continue

        # Check if previous chunk is same type → merge text
        if merged and merged[-1].get("type") == doc_type:
            merged[-1]["text"] += "\n" + item["text"]
            print(f"[Splitter] Merged continuation into {doc_type}")
        else:
            merged.append(item)

    final_chunks = [item["text"] for item in merged]
    print(f"[Splitter] Final: {len(final_chunks)} document chunks after filtering")
    return final_chunks


def _split_by_keywords(text: str) -> List[str]:
    """
    Fallback: scan through a single text block and split at document title lines.
    Used when Agent 1 doesn't insert delimiters (e.g., single-page PDFs).
    """
    lines = text.split("\n")

    # Build combined pattern from all document titles
    all_patterns = []
    for patterns in DOCUMENT_TITLES.values():
        all_patterns.extend(patterns)
    combined = "|".join(all_patterns)

    boundary_indices: List[int] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or len(stripped) > 120:
            continue

        if re.search(combined, stripped, re.IGNORECASE):
            # Verify it's likely a title (short line, or preceded by blank)
            is_title = (
                len(stripped) < 80
                or stripped.upper() == stripped
                or i == 0
                or (i > 0 and not lines[i - 1].strip())
            )
            if is_title:
                boundary_indices.append(i)

    if not boundary_indices:
        return [text.strip()] if text.strip() else []

    chunks: List[str] = []

    # Text before first boundary
    if boundary_indices[0] > 0:
        preamble = "\n".join(lines[:boundary_indices[0]]).strip()
        if preamble and len(preamble) > 50:
            chunks.append(preamble)

    # Build chunks from boundaries
    for idx, start in enumerate(boundary_indices):
        end = boundary_indices[idx + 1] if idx + 1 < len(boundary_indices) else len(lines)
        chunk = "\n".join(lines[start:end]).strip()
        if chunk and len(chunk) > 50:
            chunks.append(chunk)

    print(f"[Splitter] Keyword split: {len(chunks)} document chunks")
    return chunks
