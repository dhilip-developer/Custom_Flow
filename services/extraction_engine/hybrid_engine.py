"""
Hybrid Engine — The core orchestrator for the modular extraction pipeline.
"""
import asyncio
from typing import Dict, Any, List
from services.intelligence_utils import extract_chunk_with_gemini
from .segmentation import segment_documents
from .validation import validate_fields, normalize, remove_empty_docs
from .merge import merge_documents
from .extractors import EXTRACTOR_MAP
import re

async def extract_with_hybrid_engine(raw_text: str) -> Dict[str, Any]:
    """
    Final Hybrid Pipeline (Blueprint Alignment):
    1. Segment -> 2. Extract (Doc-Locked) -> 3. Validate -> 4. Normalize -> 5. Merge -> 6. Prune.
    """
    if not raw_text or not raw_text.strip():
        return {"documents": []}

    # 🔷 Step 1: Segmentation
    segments = segment_documents(raw_text)
    print(f"[HybridEngine] [LOG] Segmented into {len(segments)} document blocks.")

    all_docs = []

    # 🔷 Step 2: Parallel Extraction with Concurrency Gate (429 Prevention)
    # Using a semaphore to limit concurrent LLM requests to 5.
    semaphore = asyncio.Semaphore(5)

    async def sem_extract(seg_text, doc_type):
        async with semaphore:
            return await extract_chunk_with_gemini(seg_text, doc_type)

    extraction_tasks = []
    for seg in segments:
        extraction_tasks.append(sem_extract(seg["text"], seg["document_type"]))
    
    extraction_results = await asyncio.gather(*extraction_tasks)

    llm_failed_global = any(d.get("llm_failed") for docs in extraction_results for d in docs if isinstance(d, dict))

    for i, docs_in_chunk in enumerate(extraction_results):
        seg = segments[i]
        
        # 🔷 Step 3-6: Clean and Guard each document in the chunk
        for d in docs_in_chunk:
            # Application of the "Security Guard" (Rule Engine)
            d = validate_fields(d)
            d = normalize(d)
            
            all_docs.append(d)

    # 🔷 Step 7: Strict Merging (Removes duplicates, handles multi-page)
    all_docs = merge_documents(all_docs)

    # 🔷 Step 8: Final Pruning (Removes garbage/empty docs)
    all_docs = remove_empty_docs(all_docs)

    print(f"[HybridEngine] [LOG] Pipeline Complete. Found {len(all_docs)} unique documents.")

    global_errors = [d.get("error") for d in all_docs if d.get("error")]
    error_msg = " | ".join(set(global_errors)) if global_errors else None

    return {
        "documents": all_docs,
        "extraction_mode": "hybrid",
        "llm_failed": llm_failed_global,
        "error": error_msg
    }
