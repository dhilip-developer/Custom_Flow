"""
Merge Engine — Deduplicates and merges extracted documents.
"""
from typing import List, Dict, Any

def merge_documents(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Step 7: Global Merge & Deduplication (Final Blueprint Alignment).
    Uses strict key: (doc_type, invoice_number, bl_number).
    Handles orphans (no ID) by merging into the most confident sibling.
    """
    if not docs: return []
    
    merged = {}
    orphans = []

    for doc in docs:
        dtype = doc.get("document_type", "unknown")
        data = doc.get("structured_data", {})

        invoice_no = str(data.get("invoice_number") or "").strip().upper()
        bl_no = str(data.get("bl_number") or "").strip().upper()
        
        # Identify if this is a primary doc (has ID) or an orphan (no ID)
        if not invoice_no and not bl_no:
            orphans.append(doc)
            continue

        key = (dtype, invoice_no or "NA", bl_no or "NA")

        if key not in merged:
            merged[key] = doc
        else:
            # Merge fields
            base_data = merged[key]["structured_data"]
            for k, v in data.items():
                if v and not base_data.get(k):
                    base_data[k] = v
            # Merge items
            if "items" in data and isinstance(data["items"], list):
                if "items" not in base_data: base_data["items"] = []
                base_data["items"].extend(data["items"])

    # 🔷 Orphan Resolution Logic (User Request Fix)
    # Attach orphans to the most confident doc of the same type
    for orphan in orphans:
        dtype = orphan.get("document_type", "unknown")
        # Find candidates of same type
        candidates = [d for d in merged.values() if d.get("document_type") == dtype]
        if candidates:
            # Pick the first one since confidence_score is no longer provided by Agent 2
            primary = candidates[0]
            primary_data = primary["structured_data"]
            for k, v in orphan.get("structured_data", {}).items():
                if v and not primary_data.get(k):
                    primary_data[k] = v
        else:
            # No primary found, keep as standalone
            merged[("orphan", dtype, id(orphan))] = orphan
                
    return list(merged.values())
