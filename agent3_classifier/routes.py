"""
Routes for Agent 2: Document Classifier
"""
from fastapi import APIRouter, Body, HTTPException
from typing import List
from models.schemas import ClassificationResponse
import services.document_processor as processor
import asyncio

router = APIRouter()


from services.intelligence_utils import verify_extracted_data_async, run_customs_intelligence_async
from models.schemas import (
    VerificationRequest, VerificationResponse, 
    BatchVerificationRequest, BatchVerificationResponse,
    CustomsAuditRequest, CustomsIntelligenceResponse
)

@router.post("/verify-data", response_model=VerificationResponse, tags=["Agent 3: Classifier & Verifier"])
async def verify_data(request: VerificationRequest):
    """
    Agent 3: High-Confidence Data Verification.
    Submit the extracted JSON data from Agent 2 to verify if it supports the document type.
    Checks for mandatory values and valid document patterns.
    """
    if not request.structured_data:
        raise HTTPException(status_code=400, detail="No structured data provided for verification.")
        
    verification = await verify_extracted_data_async(request.document_type, request.structured_data)
    
    return verification


@router.post("/verify-batch", response_model=BatchVerificationResponse, tags=["Agent 3: Classifier & Verifier"])
async def verify_batch(request: BatchVerificationRequest):
    """
    Agent 3 Batch Mode: Verifies multiple documents in parallel.
    """
    if not request.documents:
        return BatchVerificationResponse(total_verified=0, results=[])
        
    tasks = [verify_extracted_data_async(doc.document_type, doc.structured_data) for doc in request.documents]
    results = await asyncio.gather(*tasks)
    
    verified_count = sum(1 for r in results if r.status == "VERIFIED")
    
    return BatchVerificationResponse(total_verified=verified_count, results=results)


@router.post("/analyze", response_model=CustomsIntelligenceResponse, tags=["Agent 3: Customs Intelligence Engine"])
async def analyze_documents(request: CustomsAuditRequest):
    """
    Agent 3: Deep Customs Intelligence Audit.
    Performs validation, cross-document checks, and customs readiness assessment.
    """
    if not request.documents:
        raise HTTPException(status_code=400, detail="No documents provided for analysis.")
        
    # Wrap in payload format expected by the engine
    payload = {"documents": request.documents}
    result = await run_customs_intelligence_async(payload)
    
    return result
