"""
Value Normalizer — Cleans and standardizes extracted field values.
Handles numbers, weights, dates, and whitespace from OCR text.
"""
import re
from typing import Any, Dict, Optional


def clean_whitespace(value: str) -> str:
    """Remove excessive whitespace, newlines, and control chars."""
    if not value:
        return ""
    cleaned = re.sub(r"[\r\n\t]+", " ", value)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()


def normalize_number(value: str) -> Optional[float]:
    """
    '3,032,800.00' → 3032800.0
    '21,749.200' → 21749.2
    'USD 5,000' → 5000.0
    Returns None if no number found.
    """
    if not value:
        return None
    # Strip currency symbols & labels
    stripped = re.sub(r"[A-Za-z$€£¥₹\s]", "", str(value))
    # Remove commas
    stripped = stripped.replace(",", "")
    # Find the first valid number
    match = re.search(r"-?\d+\.?\d*", stripped)
    if match:
        num = float(match.group())
        # Return int if whole number
        return int(num) if num == int(num) else num
    return None


def normalize_weight(value: str) -> Optional[float]:
    """
    '21,749.200 KG' → 21749.2
    '1500 KGS' → 1500.0
    '3.5 MT' → 3500.0 (metric tons → kg)
    """
    if not value:
        return None
    is_mt = bool(re.search(r"\bMT\b", str(value), re.IGNORECASE))
    num = normalize_number(value)
    if num is not None and is_mt:
        num = num * 1000  # Convert MT to KG
    return num


def normalize_date(value: str) -> Optional[str]:
    """
    Attempts to normalize dates to DD/MM/YYYY.
    Handles: DD-MM-YYYY, DD.MM.YYYY, MM/DD/YYYY (heuristic), YYYY-MM-DD, 'Apr 07, 2026'
    """
    if not value:
        return None
    text = clean_whitespace(str(value))

    # ISO: YYYY-MM-DD
    m = re.match(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", text)
    if m:
        return f"{m.group(3).zfill(2)}/{m.group(2).zfill(2)}/{m.group(1)}"

    # DD-MM-YYYY or DD/MM/YYYY or DD.MM.YYYY
    m = re.match(r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})", text)
    if m:
        day, month, year = m.group(1), m.group(2), m.group(3)
        # Heuristic: if day > 12, it's DD/MM/YYYY for sure
        # If month > 12, swap (it was MM/DD/YYYY)
        if int(month) > 12:
            day, month = month, day
        return f"{day.zfill(2)}/{month.zfill(2)}/{year}"

    # DD-MM-YY
    m = re.match(r"(\d{1,2})[./-](\d{1,2})[./-](\d{2})\b", text)
    if m:
        day, month, year = m.group(1), m.group(2), "20" + m.group(3)
        if int(month) > 12:
            day, month = month, day
        return f"{day.zfill(2)}/{month.zfill(2)}/{year}"

    # Named month: 'Apr 07, 2026' or '7 April 2026'
    MONTHS = {
        "jan": "01", "feb": "02", "mar": "03", "apr": "04",
        "may": "05", "jun": "06", "jul": "07", "aug": "08",
        "sep": "09", "oct": "10", "nov": "11", "dec": "12",
        "january": "01", "february": "02", "march": "03",
        "april": "04", "june": "06", "july": "07",
        "august": "08", "september": "09", "october": "10",
        "november": "11", "december": "12",
    }
    m = re.match(
        r"(\d{1,2})\s*(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})", text
    )
    if m:
        day = m.group(1).zfill(2)
        month = MONTHS.get(m.group(2).lower()[:3], "00")
        return f"{day}/{month}/{m.group(3)}"

    m = re.match(
        r"([A-Za-z]+)\s+(\d{1,2})\s*(?:st|nd|rd|th)?\s*,?\s*(\d{4})", text
    )
    if m:
        month = MONTHS.get(m.group(1).lower()[:3], "00")
        day = m.group(2).zfill(2)
        return f"{day}/{month}/{m.group(3)}"

    # Fallback — return original cleaned text
    return text


def normalize_container_number(value: str) -> Optional[str]:
    """Extract ISO 6346 container number: XXXX1234567"""
    if not value:
        return None
    m = re.search(r"[A-Z]{4}\d{7}", str(value).upper())
    return m.group() if m else clean_whitespace(value)


def prune_empty_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove keys with null, empty, 'N/A', or 'n/a' values."""
    return {
        k: v for k, v in data.items()
        if v is not None
        and str(v).strip() not in ("", "N/A", "n/a", "NA", "None", "null", "-", "—")
    }
