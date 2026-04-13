import re
from typing import List, Dict


class FastFilter:
    """
    V3 Filter: Identifies pages that are clearly NOT customs documents
    using compound keyword patterns. Skips only high-confidence junk.
    
    Philosophy: When in doubt, keep the page. Let the AI classifier decide.
    Only skip pages that are DEFINITELY irrelevant (pure T&C, legal boilerplate).
    """

    # Compound patterns that indicate customs-relevant content
    RELEVANT_PATTERNS = [
        r"invoice",
        r"bill\s*of\s*lading",
        r"packing\s*list",
        r"certificate\s*of\s*(origin|analysis)",
        r"weight\s*note",
        r"high\s*sea\s*sale",
        r"consignee",
        r"shipper",
        r"hs\s*code",
        r"freight",
        r"insurance",
        r"iec\s*(code|certificate|number)",
        r"gst\s*(number|certificate|no)",
        r"pan\s*(card|number|no)",
        r"authorization\s*letter",
        r"customs",
        r"import",
        r"export",
        r"port\s*of\s*(loading|discharge|destination)",
        r"vessel",
        r"container\s*no",
        r"seal\s*no",
        r"b/l\s*no",
        r"gross\s*weight",
        r"net\s*weight",
        r"quantity",
        r"unit\s*price",
        r"total\s*amount",
        r"country\s*of\s*origin",
        r"description\s*of\s*goods",
    ]

    # High-confidence junk patterns (only skip if NONE of the relevant patterns match)
    JUNK_PATTERNS = [
        r"terms\s+and\s+conditions",
        r"general\s+conditions",
        r"arbitration\s+clause",
        r"indemnification",
        r"force\s+majeure",
        r"governing\s+law",
        r"limitation\s+of\s+liability",
        r"privacy\s+policy",
        r"disclaimer",
    ]

    @classmethod
    def analyze(cls, pages: List[Dict]) -> List[Dict]:
        """
        Marks each page as relevant=True/False.
        Scanned pages (no text) are ALWAYS marked relevant.
        """
        for p in pages:
            text = p.get("text", "").lower()

            # Scanned pages: no text to filter on — always keep
            if not text or len(text) < 30:
                p["relevant"] = True
                p["filter_reason"] = "scanned_page"
                continue

            has_relevant = any(re.search(pat, text) for pat in cls.RELEVANT_PATTERNS)
            has_junk = any(re.search(pat, text) for pat in cls.JUNK_PATTERNS)

            if has_relevant:
                p["relevant"] = True
                p["filter_reason"] = "keywords_matched"
            elif has_junk:
                p["relevant"] = False
                p["filter_reason"] = "junk_detected"
            else:
                # Ambiguous — keep it, let the classifier decide
                p["relevant"] = True
                p["filter_reason"] = "ambiguous_kept"

        relevant_count = sum(1 for p in pages if p.get("relevant"))
        skipped_count = len(pages) - relevant_count
        print(f"[Filter] {relevant_count} relevant, {skipped_count} skipped")
        return pages
