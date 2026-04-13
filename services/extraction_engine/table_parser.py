"""
Table Parser — Detects and extracts tabular line-item data from OCR text.
Handles Invoice item rows, Packing List product lines, etc.
"""
import re
from typing import List, Dict, Optional


# Common header keywords that signal the start of a table
TABLE_HEADER_PATTERNS = [
    r"(?:S\.?\s*No|Sr\.?\s*No|Sl\.?\s*No)",
    r"Description\s*(?:of\s*Goods)?",
    r"Material\s*Description",
    r"Part\s*(?:No|Number)",
    r"HSN\s*(?:Code|/SAC)",
    r"Quantity|Qty",
    r"Unit\s*Price|Rate",
    r"Amount|Total|Value",
]

# Signals end of table
TABLE_END_PATTERNS = [
    r"Total\s*(?:Amount|Value|Invoice)",
    r"Grand\s*Total",
    r"Sub\s*Total",
    r"Tax\s*(?:Amount|Total)",
    r"(?:In\s*Words|Amount\s*in\s*Words)",
    r"(?:Terms\s*(?:and|&)\s*Conditions)",
    r"(?:Bank\s*Details)",
    r"(?:Authorised\s*Signatory)",
]


def find_table_boundaries(text: str) -> tuple:
    """
    Returns (start_index, end_index) of the table region in the text.
    Returns (0, len(text)) if boundaries cannot be detected.
    """
    lines = text.split("\n")
    start_line = 0
    end_line = len(lines)

    # Find header row
    combined_header = "|".join(TABLE_HEADER_PATTERNS)
    for i, line in enumerate(lines):
        matches = len(re.findall(combined_header, line, re.IGNORECASE))
        if matches >= 2:  # At least 2 header keywords on same line
            start_line = i + 1  # Data starts after header
            break

    # Find footer / total row
    combined_end = "|".join(TABLE_END_PATTERNS)
    for i in range(start_line, len(lines)):
        if re.search(combined_end, lines[i], re.IGNORECASE):
            end_line = i
            break

    return start_line, end_line


def extract_line_items(text: str) -> List[Dict[str, Optional[str]]]:
    """
    Extract tabular line items from OCR text.
    Returns list of dicts with keys: name, quantity, unit_price, total_price, hsn_code, batch
    """
    start, end = find_table_boundaries(text)
    lines = text.split("\n")[start:end]

    items: List[Dict[str, Optional[str]]] = []

    for line in lines:
        line = line.strip()
        if not line or len(line) < 10:
            continue

        # Skip lines that are just dashes, equals, or underscores (table borders)
        if re.match(r"^[-=_\s|+]+$", line):
            continue

        # Skip lines that are purely numeric (page numbers, etc.)
        if re.match(r"^\d{1,3}$", line):
            continue

        item = _parse_item_line(line)
        if item and (item.get("name") or item.get("quantity")):
            items.append(item)

    return items


def _parse_item_line(line: str) -> Optional[Dict[str, Optional[str]]]:
    """
    Parse a single line from a table row into structured fields.
    Uses number-position heuristics since OCR doesn't preserve columns.
    """
    # Find all number groups in the line (potential qty, price, amount)
    number_pattern = r"(\d[\d,]*\.?\d*)"
    numbers = re.findall(number_pattern, line)

    # Find HSN code (4-8 digit standalone number, typically 8 digits)
    hsn = None
    hsn_match = re.search(r"\b(\d{4}(?:\.\d{2}(?:\.\d{2})?)?)\b", line)
    if hsn_match:
        candidate = hsn_match.group(1).replace(".", "")
        if 4 <= len(candidate) <= 8:
            hsn = hsn_match.group(1)

    # Extract the text portion (description) — everything before the first number cluster
    # or the longest non-numeric segment
    text_parts = re.split(r"\s{2,}|\t+", line)

    name = None
    quantity = None
    unit_price = None
    total_price = None
    batch = None

    # Strategy: First text-heavy segment = name, numbers = qty/price/amount
    for part in text_parts:
        part = part.strip()
        if not part:
            continue
        # If part is mostly alphabetic, it's likely the description
        alpha_ratio = sum(1 for c in part if c.isalpha()) / max(len(part), 1)
        if alpha_ratio > 0.5 and not name:
            name = part
        elif re.match(r"^[\d,.\s]+$", part) and not quantity:
            quantity = part.strip()

    # If we found numbers, assign them based on count
    # Common patterns: [qty, rate, amount] or [qty, amount] or [amount]
    clean_numbers = []
    for n in numbers:
        val = n.replace(",", "")
        try:
            float(val)
            # Skip HSN codes from the number list
            if hsn and n.replace(".", "") == hsn.replace(".", ""):
                continue
            clean_numbers.append(n)
        except ValueError:
            continue

    if len(clean_numbers) >= 3:
        quantity = quantity or clean_numbers[0]
        unit_price = clean_numbers[-2]
        total_price = clean_numbers[-1]
    elif len(clean_numbers) == 2:
        quantity = quantity or clean_numbers[0]
        total_price = clean_numbers[1]
    elif len(clean_numbers) == 1:
        total_price = clean_numbers[0]

    # Batch number detection (alphanumeric like "B-2026-001" or "LOT-XYZ")
    batch_match = re.search(
        r"(?:Batch|Lot|B[/-])\s*(?:No\.?\s*)?[:：]?\s*([A-Z0-9][-A-Z0-9/]+)",
        line, re.IGNORECASE
    )
    if batch_match:
        batch = batch_match.group(1)

    if not name and not quantity and not total_price:
        return None

    return {
        "name": name,
        "quantity": quantity,
        "unit_price": unit_price,
        "total_price": total_price,
        "hsn_code": hsn,
        "batch": batch,
    }
