"""
Routes for Agent 1: OCR Text Extractor — Smart Extraction Pipeline
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from models.schemas import SmartExtractionResponse
import services.document_processor as processor

router = APIRouter()


@router.post(
    "/extract-text",
    response_model=SmartExtractionResponse,
    tags=["Agent 1: OCR Extractor"],
)
async def extract_text(file: UploadFile = File(...)):
    """
    Agent 1: Upload a document (PDF, Image, Word) and extract text
    with intelligent page-level filtering.

    Returns structured JSON with documents grouped by type (BOL, Invoice,
    Packing List, etc.) and unnecessary pages filtered out.
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file supplied")

    try:
        contents = await file.read()
        mime_type = file.content_type or "application/octet-stream"

        result = await processor.smart_extract_from_file(contents, mime_type)
        return result

    except RuntimeError as e:
        # Document AI configuration/availability errors
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent 1 extraction failed: {str(e)}")
