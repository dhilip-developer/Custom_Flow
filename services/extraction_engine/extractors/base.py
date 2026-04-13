"""
Base Extractor — Abstract base class for all document-type extractors.
"""
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from services.extraction_engine.normalizer import (
    clean_whitespace,
    normalize_number,
    normalize_weight,
    normalize_date,
    prune_empty_fields,
)


class BaseExtractor(ABC):
    """
    Each document type extractor inherits from this class
    and implements extract_fields().
    """

    @abstractmethod
    def extract_fields(self, text: str) -> Dict[str, Any]:
        """Extract all relevant fields from the raw OCR text."""
        ...

    # ── Common Regex Helpers ──

    @staticmethod
    def search_value(
        text: str,
        patterns: List[str],
        flags: int = re.IGNORECASE | re.MULTILINE,
    ) -> Optional[str]:
        """
        Try each pattern in order. Return the first captured group from the first match.
        """
        for pattern in patterns:
            m = re.search(pattern, text, flags)
            if m and m.group(1):
                return clean_whitespace(m.group(1))
        return None

    @staticmethod
    def search_block(
        text: str,
        keyword: str,
        max_lines: int = 3,
    ) -> Optional[str]:
        """
        Find a keyword in the text and return the next `max_lines` non-empty lines.
        Useful for extracting multi-line fields like Shipper/Consignee addresses.
        """
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if re.search(keyword, line, re.IGNORECASE):
                # Check if value is on the same line (after the keyword)
                after_keyword = re.sub(
                    rf".*?{keyword}\s*[:：]?\s*",
                    "",
                    line,
                    flags=re.IGNORECASE,
                ).strip()
                if after_keyword and len(after_keyword) > 3:
                    result_lines = [after_keyword]
                    for j in range(i + 1, min(i + max_lines, len(lines))):
                        next_line = lines[j].strip()
                        if not next_line:
                            break
                        # Stop if next line looks like a new field label
                        if re.match(r"^[A-Z][a-z]+.*[:：]", next_line):
                            break
                        result_lines.append(next_line)
                    return " ".join(result_lines)
                else:
                    # Value is on subsequent lines
                    result_lines = []
                    for j in range(i + 1, min(i + 1 + max_lines, len(lines))):
                        next_line = lines[j].strip()
                        if not next_line:
                            break
                        if re.match(r"^[A-Z][a-z]+.*[:：]", next_line):
                            break
                        result_lines.append(next_line)
                    if result_lines:
                        return " ".join(result_lines)
        return None

    @staticmethod
    def search_all_matches(
        text: str,
        pattern: str,
        flags: int = re.IGNORECASE,
    ) -> List[str]:
        """Return all captured group(1) matches."""
        return [m.group(1) for m in re.finditer(pattern, text, flags) if m.group(1)]

    @staticmethod
    def find_currency(text: str) -> Optional[str]:
        """Detect the primary currency in the text."""
        currencies = {
            "USD": r"\bUSD\b|\bUS\s*\$|\$",
            "INR": r"\bINR\b|₹",
            "EUR": r"\bEUR\b|€",
            "GBP": r"\bGBP\b|£",
            "JPY": r"\bJPY\b|¥",
            "AED": r"\bAED\b",
        }
        for code, pattern in currencies.items():
            if re.search(pattern, text, re.IGNORECASE):
                return code
        return None
