"""
Extraction Engine — Pure Python structured data extraction.
Zero API calls. Instant results. 100% reproducible.

Entry point: extract_structured_data(raw_text) -> SuperExtractionResponse
"""
import time
from typing import List, Dict, Any

from models.schemas import SuperExtractionResponse, SuperExtractionResult

from services.extraction_engine.splitter import split_raw_text
from services.extraction_engine.classifier import classify_all
from services.extraction_engine.extractors import EXTRACTOR_MAP
from services.extraction_engine.normalizer import prune_empty_fields


def extract_structured_data(raw_text: str) -> SuperExtractionResponse:
    """
    Main entry point — replaces the LLM-based extract_with_super_agent().

    Pipeline:
        1. Split raw_text into document chunks
        2. Classify each chunk (regex-based)
        3. Run type-specific extractor on each chunk
        4. Build SuperExtractionResponse

    Args:
        raw_text: Merged raw text from Agent 1 (documents separated by === delimiters)

    Returns:
        SuperExtractionResponse with list of extracted documents
    """
    start = time.time()
    print("[ExtractionEngine] Starting pure-Python extraction...")

    # 1. SPLIT
    chunks = split_raw_text(raw_text)
    if not chunks:
        print("[ExtractionEngine] No document chunks found in input")
        return SuperExtractionResponse(documents=[])

    # 2. CLASSIFY
    classified = classify_all(chunks)

    # 3. EXTRACT
    documents: List[SuperExtractionResult] = []
    for item in classified:
        doc_type = item["document_type"]
        text = item["text"]

        if doc_type == "unknown":
            print(f"[ExtractionEngine] Skipping unknown chunk ({len(text)} chars)")
            continue

        extractor_cls = EXTRACTOR_MAP.get(doc_type)
        if not extractor_cls:
            print(f"[ExtractionEngine] No extractor for type '{doc_type}', skipping")
            continue

        try:
            extractor = extractor_cls()
            fields = extractor.extract_fields(text)
            fields = prune_empty_fields(fields)

            if fields:
                documents.append(SuperExtractionResult(
                    document_type=doc_type,
                    structured_data=fields,
                ))
                print(f"[ExtractionEngine] ✓ {doc_type}: {len(fields)} fields extracted")
            else:
                print(f"[ExtractionEngine] ✗ {doc_type}: no fields extracted (empty result)")

        except Exception as e:
            print(f"[ExtractionEngine] Error extracting {doc_type}: {e}")

    # 4. MERGE duplicates (same type + same ID)
    documents = _merge_duplicates(documents)

    elapsed = time.time() - start
    print(f"[ExtractionEngine] Complete: {len(documents)} documents in {elapsed:.3f}s")

    return SuperExtractionResponse(documents=documents)


def _merge_duplicates(docs: List[SuperExtractionResult]) -> List[SuperExtractionResult]:
    """
    Merge documents of the same type + same identifier.
    E.g., two Invoice chunks with the same invoice_number get merged.
    """
    if len(docs) <= 1:
        return docs

    merged: Dict[str, SuperExtractionResult] = {}

    for doc in docs:
        dtype = doc.document_type
        data = doc.structured_data

        # Build a merge key from the document's primary identifier
        doc_id = str(
            data.get("invoice_number")
            or data.get("bl_number")
            or data.get("hss_ref_no")
            or data.get("pl_number")
            or ""
        ).strip().upper()

        key = f"{dtype}::{doc_id}"

        if key not in merged:
            merged[key] = doc
        else:
            # Merge fields — keep existing values, fill gaps
            base = merged[key].structured_data
            for field, value in data.items():
                if not value:
                    continue
                if not base.get(field):
                    base[field] = value
                elif field in ("items", "product_details") and isinstance(value, list):
                    existing = base.get(field, [])
                    existing.extend(value)
                    base[field] = existing
                elif isinstance(value, str) and len(str(value)) > len(str(base.get(field, ""))):
                    base[field] = value

    return list(merged.values())
