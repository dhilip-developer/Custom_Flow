import fitz
import io
import os
import asyncio
import time
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor
from google.cloud import documentai
from shared.config import load_credentials, DOCAI_CONFIG, PROJECT_ROOT

load_credentials()


class TargetedExtractor:
    """
    V3 Extractor: Sends only grouped page ranges to Document AI.
    
    Fixes from V2:
    - Client created ONCE in __init__ (not per-call)
    - Removed duplicate return statement
    - Auto-chunks groups > 15 pages
    - Detailed timing logs
    """

    MAX_PAGES_PER_REQUEST = 15

    def __init__(self):
        self.project_id = DOCAI_CONFIG["project_id"]
        self.location = DOCAI_CONFIG["location"]
        self.credentials_path = os.path.join(PROJECT_ROOT, DOCAI_CONFIG["credentials_file"])
        processor_id = DOCAI_CONFIG["processor_id"]

        # Single client instance — reused across all extraction calls
        self.client = documentai.DocumentProcessorServiceClient.from_service_account_file(
            self.credentials_path
        )
        self.processor_name = (
            f"projects/{self.project_id}/locations/{self.location}/processors/{processor_id}"
        )
        # Dedicated thread pool for IO-bound Document AI requests
        self.executor = ThreadPoolExecutor(max_workers=32)

    async def _extract_single(self, pdf_bytes: bytes, doc_type: str, label: str) -> Dict:
        """Extract text from a single PDF buffer via Document AI."""
        start = time.time()
        size_kb = len(pdf_bytes) // 1024
        print(f"[Extractor] {label} ({size_kb} KB)...")

        try:
            raw_doc = documentai.RawDocument(content=pdf_bytes, mime_type="application/pdf")
            request = documentai.ProcessRequest(
                name=self.processor_name, raw_document=raw_doc
            )
            
            # Use custom executor for higher concurrency than default
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(self.executor, lambda: self.client.process_document(request=request))

            elapsed = time.time() - start
            text = result.document.text or ""
            entities = [
                {"type": e.type_, "value": e.mention_text}
                for e in result.document.entities
            ]
            print(f"[Extractor] {label} done in {elapsed:.2f}s ({len(text)} chars)")
            return {"text": text, "entities": entities}

        except Exception as e:
            print(f"[Extractor] ERROR {label}: {e}")
            return {"text": "", "entities": [], "error": str(e)}

    def _merge_buffers(self, buffers: List[bytes]) -> bytes:
        """Combine multiple single-page PDF buffers into one PDF."""
        merged = fitz.open()
        for buf in buffers:
            page_doc = fitz.open(stream=buf, filetype="pdf")
            merged.insert_pdf(page_doc)
            page_doc.close()
        out = io.BytesIO()
        merged.save(out)
        merged.close()
        return out.getvalue()

    async def extract_single_group(self, group: Dict) -> Dict:
        """Extract text for a single document group (handles chunking)."""
        buffers = group["buffers"]
        doc_type = group["document_type"]
        pages = group["pages"]

        # Chunk large groups
        chunks = []
        for i in range(0, len(buffers), self.MAX_PAGES_PER_REQUEST):
            chunk_bufs = buffers[i : i + self.MAX_PAGES_PER_REQUEST]
            chunk_pages = pages[i : i + self.MAX_PAGES_PER_REQUEST]
            chunks.append((chunk_bufs, chunk_pages))

        tasks = []
        for chunk_bufs, chunk_pages in chunks:
            merged_pdf = self._merge_buffers(chunk_bufs)
            pg_label = f"{chunk_pages[0]}-{chunk_pages[-1]}" if len(chunk_pages) > 1 else str(chunk_pages[0])
            label = f"{doc_type} pg[{pg_label}]"
            tasks.append(self._extract_single(merged_pdf, doc_type, label))

        # Execute chunks for this group in parallel
        results = await asyncio.gather(*tasks)

        merged_text_parts = []
        merged_entities = []
        for res in results:
            if res.get("text"):
                merged_text_parts.append(res["text"])
            if res.get("entities"):
                merged_entities.extend(res["entities"])

        group["data"] = {
            "text": "\n\n".join(merged_text_parts),
            "entities": merged_entities,
        }
        return group

    async def extract_all(self, groups: List[Dict]) -> List[Dict]:
        """
        Run targeted Document AI extraction for all document groups.
        Uses extract_single_group for each group in parallel.
        """
        start = time.time()
        tasks = [self.extract_single_group(g) for g in groups]
        results = await asyncio.gather(*tasks)
        
        elapsed = time.time() - start
        print(f"[Extractor] All {len(groups)} groups extracted in {elapsed:.2f}s")
        return list(results)
