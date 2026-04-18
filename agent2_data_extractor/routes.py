"""
Routes for Agent 2: Phase 2 Structured Data Extractor
Driven exclusively by the Gemini Flash Intelligence Engine.
"""
from fastapi import APIRouter, Body, HTTPException
from typing import Union, Dict
from models.schemas import (
    BatchDataExtractionRequest,
    BatchDataExtractionResponse, SuperExtractionResponse,
)

from services.intelligence_utils import extract_with_super_agent

router = APIRouter()


@router.post("/extract-data-batch", response_model=BatchDataExtractionResponse, tags=["Agent 2: Data Extractor"])
async def extract_data_batch_route(request: BatchDataExtractionRequest):
    """
    Agent 2 Batch Mode: Processes the full output from Agent 1 (OCR Extractor).
    Extracts structured data for all documents using the Gemini Intelligence Engine.
    """
    if not request.extraction_results.raw_text:
        return BatchDataExtractionResponse(results=[])

    # Core Intelligence Engine
    super_result = await extract_with_super_agent(request.extraction_results.raw_text)

    batch_results = []
    for doc in super_result.documents:
        batch_results.append({
            "page_range": "N/A",
            "document_type": doc.document_type,
            "extracted_data": doc.structured_data,
        })

    return BatchDataExtractionResponse(results=batch_results)


@router.post("/extract-super", response_model=SuperExtractionResponse, tags=["Agent 2: Data Extractor"])
async def extract_super_route(
    payload: Union[str, Dict] = Body(..., description="Raw text or JSON object containing 'raw_text'")
):
    """
    Agent 2 SUPER MODE: Performs simultaneous classification and data extraction
    in a single pass utilizing the strict Gemini 6-stage fallback pipeline.
    """
    input_text = ""
    if isinstance(payload, dict):
        input_text = payload.get("raw_text", str(payload))
    else:
        input_text = payload

    if not input_text or len(input_text.strip()) == 0:
        raise HTTPException(status_code=400, detail="No raw text provided in payload.")

    print(f"[Agent 2] Gemini Super Engine Payload Received: {len(input_text)} chars")

    try:
        # Call Gemini Engine (extract_with_super_agent has been modified to bypass regex completely)
        results = await extract_with_super_agent(input_text)
        return results
    except Exception as e:
        import traceback
        print(f"[Agent 2] ERROR: Extraction failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Extraction Error: {str(e)}")
