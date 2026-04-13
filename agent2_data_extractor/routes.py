"""
Routes for Agent 2: Structured Data Extractor
Supports two engines: 'regex' (default, pure Python) and 'llm' (legacy API-based).
"""
from fastapi import APIRouter, Body, HTTPException, Query
from typing import Union, Dict
from models.schemas import (
    DataExtractionResponse, BatchDataExtractionRequest,
    BatchDataExtractionResponse, SuperExtractionResponse,
)
from services.extraction_engine import extract_structured_data
from services.extraction_engine.extractors import EXTRACTOR_MAP
from services.extraction_engine.normalizer import prune_empty_fields

# Legacy LLM imports (kept for fallback)
from services.intelligence_utils import (
    extract_data_from_text_async, extract_with_super_agent,
)

router = APIRouter()


@router.post("/extract-data", response_model=DataExtractionResponse, tags=["Agent 2: Data Extractor"])
async def extract_data(
    document_type: str = Query(..., description="The document type (e.g. 'Invoice', 'Bill of Lading')"),
    payload: str = Body(..., media_type="text/plain"),
    engine: str = Query("regex", description="Engine to use: 'regex' (default, pure Python) or 'llm' (legacy API-based)"),
):
    """
    Agent 2: Submit raw unformatted text to rigidly parse the exact required Key-Value fields.
    """
    if not payload or len(payload.strip()) == 0:
        raise HTTPException(status_code=400, detail="No raw text provided in payload.")

    if engine == "llm":
        # Legacy path — use LLM APIs
        extracted = await extract_data_from_text_async(document_type, payload)
        return DataExtractionResponse(extracted_data=extracted)

    # --- Regex Engine (default) ---
    # Normalize document_type to lowercase key
    type_map = {
        "invoice": "invoice",
        "bill of lading": "bill_of_lading",
        "bill of lading (bol)": "bill_of_lading",
        "packing list": "packing_list",
        "high sea sale agreement (hss)": "high_seas_sale_agreement",
        "high seas sale agreement": "high_seas_sale_agreement",
        "freight certificate": "freight_certificate",
        "insurance certificate": "insurance_certificate",
    }
    normalized_type = type_map.get(document_type.lower().strip(), document_type.lower().strip())

    extractor_cls = EXTRACTOR_MAP.get(normalized_type)
    if not extractor_cls:
        raise HTTPException(
            status_code=400,
            detail=f"No regex extractor available for type '{document_type}'. "
                   f"Available types: {list(EXTRACTOR_MAP.keys())}. "
                   f"Use engine=llm for unsupported types.",
        )

    extractor = extractor_cls()
    fields = extractor.extract_fields(payload)
    fields = prune_empty_fields(fields)

    return DataExtractionResponse(extracted_data=fields)


@router.post("/extract-data-batch", response_model=BatchDataExtractionResponse, tags=["Agent 2: Data Extractor"])
async def extract_data_batch_route(
    request: BatchDataExtractionRequest,
    engine: str = Query("regex", description="Engine: 'regex' (default) or 'llm'"),
):
    """
    Agent 2 Batch Mode: Processes the full output from Agent 1 (OCR Extractor).
    Extracts structured data for all documents.
    """
    if not request.extraction_results.raw_text:
        return BatchDataExtractionResponse(results=[])

    if engine == "llm":
        # Legacy path
        super_result = await extract_with_super_agent(request.extraction_results.raw_text)
    else:
        # Regex engine (default)
        super_result = extract_structured_data(request.extraction_results.raw_text)

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
    payload: Union[str, Dict] = Body(..., description="Raw text or JSON object containing 'raw_text'"),
    engine: str = Query("regex", description="Engine: 'regex' (default) or 'llm'"),
):
    """
    Agent 2 SUPER MODE: Performs simultaneous splitting, classification and extraction in a single pass.
    Default engine: regex (pure Python, instant, zero API cost).
    Fallback: engine=llm (uses Gemini/OpenRouter/HF APIs).
    """
    input_text = ""
    if isinstance(payload, dict):
        input_text = payload.get("raw_text", str(payload))
    else:
        input_text = payload

    if not input_text or len(input_text.strip()) == 0:
        raise HTTPException(status_code=400, detail="No raw text provided in payload.")

    print(f"[Agent 2] Super extraction request. Engine: {engine}, Input: {len(input_text)} chars")

    if engine == "llm":
        results = await extract_with_super_agent(input_text)
    else:
        results = extract_structured_data(input_text)

    return results
