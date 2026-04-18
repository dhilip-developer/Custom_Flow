import re
from typing import List, Dict

DOC_PATTERNS = {
    "invoice": r"\bINVOICE\b",
    "high_seas_sale_agreement": r"HIGH\s+SEAS\s+SALE\s+AGREEMENT",
    "bill_of_lading": r"BILL\s+OF\s+LADING|ORIGINAL\s+NON\s+NEGOTIABLE",
    "packing_list": r"PACKING\s+LIST",
    "certificate_of_origin": r"CERTIFICATE\s+OF\s+ORIGIN",
    "certificate_of_analysis": r"CERTIFICATE\s+OF\s+ANALYSIS",
    "weight_note": r"WEIGHT\s+NOTE",
    "freight_certificate": r"FREIGHT\s+CERTIFICATE|OCEAN\s+FREIGHT",
    "insurance_certificate": r"INSURANCE\s+CERTIFICATE|MARINE\s+INSURANCE"
}

def segment_documents(raw_text: str) -> List[Dict[str, str]]:
    """
    Step 1: Document Segmentation (Final Blueprint Alignment).
    Splits raw OCR text into logical blocks based on strong document anchors.
    Also implements sub-chunking for safety on massive files.
    """
    if not raw_text or not raw_text.strip():
        return []

    # --- SMALL BLOCK PROTECTION ---
    if len(raw_text) < 5000:
        block_lower = raw_text.lower()
        doc_type = "unknown"
        if "invoice" in block_lower or "bill of supply" in block_lower: doc_type = "invoice"
        elif "lading" in block_lower or "waybill" in block_lower: doc_type = "bill_of_lading"
        elif "hss" in block_lower or "high seas" in block_lower: doc_type = "high_seas_sale_agreement"
        elif "packing" in block_lower: doc_type = "packing_list"
        elif "freight" in block_lower: doc_type = "freight_certificate"
        elif "insurance" in block_lower: doc_type = "insurance_certificate"
        
        return [{"document_type": doc_type, "text": raw_text.strip()}]

    # 🔷 Regex-based Split Logic (User Requirement Alignment)
    # Using the patterns at the top of the file for precise identification
    all_patterns = []
    for dtype, pattern in DOC_PATTERNS.items():
        all_patterns.append(f"(?P<{dtype}>{pattern})")
    
    master_pattern = "|".join(all_patterns)
    
    # We use re.finditer to get positions of all anchors
    matches = list(re.finditer(master_pattern, raw_text, flags=re.IGNORECASE))
    
    segments = []
    if not matches:
        # Fallback to single block if no anchors found but over 5000 chars
        segments.append({"document_type": "unknown", "text": raw_text})
    else:
        # Split based on match positions
        for i in range(len(matches)):
            start = matches[i].start()
            end = matches[i+1].start() if i+1 < len(matches) else len(raw_text)
            
            # Determine type from the match group names
            match_groups = matches[i].groupdict()
            doc_type = next((k for k, v in match_groups.items() if v), "unknown")
            
            segments.append({
                "document_type": doc_type,
                "text": raw_text[start:end].strip()
            })

    # 🔷 SAFETY SUB-CHUNKING (The "Shredder")
    # If any segment is > 12k chars, split it further to prevent LLM timeouts/failures.
    final_segments = []
    MAX_CHARS = 12000
    OVERLAP = 1000

    for seg in segments:
        text = seg["text"]
        if len(text) <= MAX_CHARS:
            final_segments.append(seg)
        else:
            # Split into overlapping chunks
            print(f"[Segmentation] Segment {seg['document_type']} too large ({len(text)} chars). Sub-chunking...")
            curr = 0
            while curr < len(text):
                chunk_text = text[curr : curr + MAX_CHARS]
                final_segments.append({
                    "document_type": seg["document_type"],
                    "text": chunk_text
                })
                curr += (MAX_CHARS - OVERLAP)
                if curr >= len(text): break

    return final_segments
