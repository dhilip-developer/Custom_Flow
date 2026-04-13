import asyncio
import json
import time
from typing import List, Dict
from shared.config import load_credentials

load_credentials()


class DocumentClassifier:
    """
    V3 Classifier: Processes relevant pages and classifies them using Mixtral (Hugging Face).
    """

    # Types that are actual customs documents (not junk/continuation)
    CUSTOMS_TYPES = {
        "Invoice", "Bill of Lading (BOL)", "Packing List",
        "Certificate of Origin", "Certificate of Analysis",
        "Weight Note", "High Sea Sale Agreement (HSS)",
        "Insurance Certificate", "Freight Certificate",
        "IEC Certificate", "GST Certificate", "PAN Card", 
        "Authorization Letter", "Additional Documents"
    }

    SKIP_TYPES = {"terms_and_conditions", "cover_letter", "skipped", "unknown"}

    def __init__(self):
        pass

    async def classify_batch(self, pages: List[Dict]) -> List[Dict]:
        """
        Processes relevant pages and classifies them using Mixtral (Hugging Face).
        """
        from services.intelligence_utils import classify_document_async
        
        start = time.time()
        relevant_pages = [p for p in pages if p.get("relevant", True)]
        skipped_pages = [p for p in pages if not p.get("relevant", True)]

        if not relevant_pages:
            return pages

        # Run classification in parallel for all relevant pages
        tasks = []
        for p in relevant_pages:
            text = p.get("text", "")
            tasks.append(classify_document_async(text))

        print(f"[Classifier] Sending {len(relevant_pages)} pages to Mixtral...")
        results = await asyncio.gather(*tasks)

        # Map results back to pages
        for i, p in enumerate(relevant_pages):
            res_list = results[i]
            doc_type = "unknown"
            conf = 0.0
            
            if res_list:
                doc_type = res_list[0].document_type
                conf = res_list[0].confidence
            
            # --- IMPROVED HEURISTIC RECOVERY (Safety Net) ---
            # If the AI says 'unknown' but the page was previously marked RELEVANT by FastFilter,
            # we must NOT skip it. We recover it as 'Additional Documents' to ensure processing.
            if doc_type.lower() in ("unknown", "skipped", "error"):
                is_hinted = p.get("is_new_document_hint", False)
                was_marked_relevant = p.get("relevant", False)
                
                if is_hinted or was_marked_relevant:
                    print(f"[Classifier] Page {p['page_number']} recovery: HINT={is_hinted}, RELEVANT={was_marked_relevant}. Forcing keep.")
                    doc_type = "Additional Documents"
                    conf = 0.5
                
            p["document_type"] = doc_type
            p["confidence"] = conf

        # Mark skipped pages (those that were filtered out by FastFilter entirely)
        for p in skipped_pages:
            p["document_type"] = "skipped"
            p["confidence"] = 1.0

        elapsed = time.time() - start
        print(f"[Classifier] {len(relevant_pages)} pages classified in {elapsed:.2f}s using Mixtral")
        return pages
