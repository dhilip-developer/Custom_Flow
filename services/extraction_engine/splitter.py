"""
Document Splitter — Splits merged raw text from Agent 1 into individual document chunks.
Uses delimiter detection + keyword boundary scanning.
"""
import re
from typing import List, Tuple


# Document-start keywords (case-insensitive)
DOCUMENT_START_PATTERNS = [
    r"BILL\s+OF\s+LADING",
    r"\bB/L\b",
    r"OCEAN\s+BILL",
    r"MASTER\s+BILL",
    r"HOUSE\s+BILL",
    r"SEA\s+WAYBILL",
    r"COMBINED\s+TRANSPORT",
    r"COMMERCIAL\s+INVOICE",
    r"\bINVOICE\b(?!\s*(?:No|Number|#|Date))",  # "INVOICE" as a title, not "Invoice No:"
    r"TAX\s+INVOICE",
    r"PROFORMA\s+INVOICE",
    r"PACKING\s+LIST",
    r"PACKING\s+SLIP",
    r"PACKING\s+NOTE",
    r"WEIGHT\s+LIST",
    r"FREIGHT\s+CERTIFICATE",
    r"FREIGHT\s+MEMO",
    r"FREIGHT\s+INVOICE",
    r"INSURANCE\s+CERTIFICATE",
    r"CERTIFICATE\s+OF\s+INSURANCE",
    r"INSURANCE\s+POLICY",
    r"HIGH\s+SEA(?:S)?\s+SALE\s+AGREEMENT",
    r"HSS\s+AGREEMENT",
    r"CERTIFICATE\s+OF\s+ORIGIN",
]


def split_raw_text(raw_text: str) -> List[str]:
    """
    Split merged raw text from Agent 1 into individual document chunks.

    Agent 1 merges documents with '===' delimiters:
        doc1_text\\n===...===\\ndoc2_text

    If no delimiters found, falls back to keyword-based boundary detection.
    """
    if not raw_text or not raw_text.strip():
        return []

    # --- Strategy 1: Split by Agent 1's === delimiter ---
    delimiter_pattern = r"\n\s*={10,}\s*\n"
    segments = re.split(delimiter_pattern, raw_text)
    segments = [s.strip() for s in segments if s.strip() and len(s.strip()) > 50]

    if len(segments) > 1:
        print(f"[Splitter] Delimiter split: {len(segments)} document chunks")
        return segments

    # --- Strategy 2: Keyword boundary detection ---
    return _split_by_keywords(raw_text)


def _split_by_keywords(text: str) -> List[str]:
    """
    Scan through the text and split at lines that match document-start patterns.
    Only triggers on patterns that appear in the first 5 lines of a potential document.
    """
    lines = text.split("\n")
    combined_pattern = "|".join(DOCUMENT_START_PATTERNS)

    # Find all lines that look like document starts
    boundary_indices: List[int] = []
    for i, line in enumerate(lines):
        # Only consider lines in first ~5 lines of their potential doc,
        # OR lines that are clearly title-like (short, uppercase)
        stripped = line.strip()
        if not stripped:
            continue

        is_title_like = len(stripped) < 80 and stripped.upper() == stripped
        if re.search(combined_pattern, stripped, re.IGNORECASE):
            # Avoid false positives: "Invoice No: 123" in the middle of a doc
            # vs "COMMERCIAL INVOICE" as a title
            if is_title_like or i == 0 or (i > 0 and not lines[i - 1].strip()):
                boundary_indices.append(i)

    if not boundary_indices:
        print("[Splitter] No document boundaries found — returning as single chunk")
        return [text.strip()] if text.strip() else []

    # Build chunks from boundaries
    chunks: List[str] = []
    for idx, start in enumerate(boundary_indices):
        end = boundary_indices[idx + 1] if idx + 1 < len(boundary_indices) else len(lines)
        chunk = "\n".join(lines[start:end]).strip()
        if chunk and len(chunk) > 50:
            chunks.append(chunk)

    # Handle text before the first boundary
    if boundary_indices[0] > 0:
        preamble = "\n".join(lines[: boundary_indices[0]]).strip()
        if preamble and len(preamble) > 50:
            chunks.insert(0, preamble)

    print(f"[Splitter] Keyword split: {len(chunks)} document chunks")
    return chunks
