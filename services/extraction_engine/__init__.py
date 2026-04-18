"""
Extraction Engine — Modular Entry Point.
"""
from .hybrid_engine import extract_with_hybrid_engine

# Primary Entry Point
async def extract_structured_data(raw_text: str):
    """
    Main entry point for Agent 2. 
    Processes raw OCR text and returns structured customs documents.
    """
    return await extract_with_hybrid_engine(raw_text)

# Legacy exports for backwards compatibility
from .classifier import classify_chunk
from .post_processor import merge_documents as legacy_merge_documents
from .normalizer import normalize_number, normalize_date
