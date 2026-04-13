"""
FastAPI routes for the Insurance Requirement Detection Agent.
"""

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Body, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from shared.insurance_app.agent import InsuranceAgent
from shared.insurance_app.models.schemas import AgentResult, BatchResultItem, BatchResponse, ExpandedBillOfLading

ui_router = APIRouter()
agent1_router = APIRouter()
agent2_router = APIRouter()

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

agent = InsuranceAgent()

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# ── Pages ───────────────────────────────────────────────────────────

@ui_router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main landing page with links to the separated Agents."""
    return templates.TemplateResponse(request=request, name="landing.html")

@ui_router.get("/agent1", response_class=HTMLResponse)
async def serve_agent1(request: Request):
    """Serve Agent 1: Insurance Detection."""
    return templates.TemplateResponse(request=request, name="agent1.html")

@ui_router.get("/agent2", response_class=HTMLResponse)
async def serve_agent2(request: Request):
    """Serve Agent 2: Bill of Lading Extractor."""
    return templates.TemplateResponse(request=request, name="agent2.html")


# ── API ─────────────────────────────────────────────────────────────

from pydantic import BaseModel

class TextPayload(BaseModel):
    text: str

class MultiTextPayload(BaseModel):
    invoice_text: str
    packing_list_text: str
    bol_text: str

class BatchTextPayload(BaseModel):
    texts: List[str]

@agent1_router.post("/analyze/text", response_model=AgentResult)
async def analyze_text_endpoint(payload: TextPayload):
    """Accept raw plain text string and analyze it."""
    from shared.insurance_app.engine.pdf_extractor import extract_data_from_text
    try:
        data = extract_data_from_text(payload.text)
        result = agent.analyze(data)
        return result
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))

@agent1_router.get("/status")
async def get_agent1_status():
    """Returns whether the AI engine is active or in local fallback mode."""
    from shared.insurance_app.engine.detector import is_ai_enabled
    return {"ai_enabled": is_ai_enabled()}

@agent1_router.post("/analyze/text/triple", response_model=AgentResult, summary="Agent 1: Triple Text JSON Body")
async def analyze_triple_text(payload: MultiTextPayload):
    """
    Accepts three separate text strings for Invoice, PL, and BOL in a JSON body.
    Uses high-precision AI if enabled.
    """
    try:
        result = agent.analyze_triple_text(
            payload.invoice_text, 
            payload.packing_list_text, 
            payload.bol_text
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))

@agent1_router.post("/analyze", response_model=AgentResult)
async def analyze(payload: Dict[str, Any]):
    """Accept shipping documents JSON and return insurance analysis."""
    try:
        result = agent.analyze(payload)
        return result
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@agent1_router.post("/upload", response_model=AgentResult)
async def upload_file(file: UploadFile = File(...)):
    """Accept a JSON or PDF file upload, parse it, and return insurance analysis."""
    # Validate file type
    valid_types = ("application/json", "text/json", "text/plain", "application/pdf")
    name = file.filename or ""
    name_lower = name.lower()
    
    if file.content_type not in valid_types and not (name_lower.endswith(".json") or name_lower.endswith(".pdf")):
        raise HTTPException(
            status_code=400,
            detail="Only JSON and PDF files are accepted.",
        )

    try:
        content = await file.read()
        if name_lower.endswith(".pdf") or file.content_type == "application/pdf":
            from shared.insurance_app.engine.pdf_extractor import extract_data_from_pdf
            payload = extract_data_from_pdf(content)
        else:
            payload = json.loads(content.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file.")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(exc)}")

    try:
        result = agent.analyze(payload)
        return result
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@agent1_router.post("/analyze/multifile", response_model=AgentResult, summary="Agent 1: Read Multiple Direct Texts")
async def analyze_multiple_documents(
    invoice_text: str = Form(..., description="Paste Invoice text here"),
    packing_list_text: str = Form(..., description="Paste Packing List text here"),
    bol_text: str = Form(..., description="Paste Bill of Lading text here")
):
    """
    Directly paste text for each document type to test cross-checks.
    """
    from shared.insurance_app.engine.pdf_extractor import extract_data_from_text
    
    try:
        inv_data = extract_data_from_text(invoice_text)
        pl_data = extract_data_from_text(packing_list_text)
        bol_data = extract_data_from_text(bol_text)
        # Merge into a single ShippingDocuments payload
        combined_payload = {
            "invoice": inv_data.get("invoice", {}),
            "packing_list": pl_data.get("packing_list", {}),
            "bill_of_lading": bol_data.get("bill_of_lading", {})
        }
        
        # Ensure BOL uses common shipping data if found in Invoice (like port of loading)
        if not combined_payload["bill_of_lading"].get("port_of_loading") or combined_payload["bill_of_lading"]["port_of_loading"].startswith("POL NOT"):
            combined_payload["bill_of_lading"]["port_of_loading"] = inv_data.get("bill_of_lading", {}).get("port_of_loading")

        result = agent.analyze(combined_payload)
        return result
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@agent1_router.post("/analyze/batch", response_model=BatchResponse, summary="Analyze a batch of N documents")
async def analyze_batch(files: List[UploadFile] = File(...)):
    """
    Upload an arbitrary number of documents (.json or .pdf) and analyze them in batch.
    Returns a list of results mapping each filename to its analysis output or error.
    """
    responses = []
    for file in files:
        name = file.filename or "unknown"
        name_lower = name.lower()
        
        try:
            content = await file.read()
            if not content:
                continue

            if name_lower.endswith(".pdf") or file.content_type == "application/pdf":
                from shared.insurance_app.engine.pdf_extractor import extract_data_from_pdf
                payload = extract_data_from_pdf(content)
            elif name_lower.endswith(".json") or file.content_type in ("application/json", "text/json"):
                payload = json.loads(content.decode("utf-8"))
            else:
                responses.append(BatchResultItem(filename=name, result=None, error="Unsupported format. Use .json or .pdf."))
                continue
            
            result = agent.analyze(payload)
            responses.append(BatchResultItem(filename=name, result=result, error=None))
        except Exception as exc:
            responses.append(BatchResultItem(filename=name, result=None, error=str(exc)))
            
    return BatchResponse(results=responses)


# ── Agent 2: Bill of Lading Extractor ──────────────────────────────

@agent1_router.post("/analyze/batch/text", response_model=BatchResponse, summary="Analyze a batch of N text blocks")
async def analyze_batch_text(payload: BatchTextPayload):
    """
    Accepts a list of raw text strings and returns a batch of insurance analysis results.
    """
    responses = []
    for i, text in enumerate(payload.texts):
        name = f"Text Block {i+1}"
        try:
            # Use high-precision AI/Heuristic routing
            result = agent.analyze_triple_text(text, "", "")
            responses.append(BatchResultItem(filename=name, result=result, error=None))
        except Exception as exc:
            responses.append(BatchResultItem(filename=name, result=None, error=str(exc)))
            
    return BatchResponse(results=responses)

@agent2_router.post("/extract/bol", response_model=ExpandedBillOfLading, summary="Agent 2: Extract 13 fields from BOL text")
async def extract_bol(
    bol_text: str = Form(..., description="Paste raw text from the Bill of Lading for 13-point extraction")
):
    """
    Dedicated endpoint for Agent 2. 
    Accepts raw Bill of Lading text and extracts specific structured data.
    """
    from shared.insurance_app.engine.bol_extractor import extract_expanded_bol
    try:
        data = extract_expanded_bol(bol_text)
        return data
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))

@agent2_router.get("/status")
async def get_agent2_status():
    """Returns whether the AI engine is active or in local fallback mode."""
    from shared.insurance_app.engine.bol_extractor import is_ai_enabled
    return {"ai_enabled": is_ai_enabled()}


@ui_router.get("/api/samples/{name}")
async def get_sample(name: str):
    """Return a sample data file by name (without .json extension)."""
    safe_name = name.replace("..", "").replace("/", "").replace("\\", "")
    filepath = DATA_DIR / f"{safe_name}.json"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Sample '{name}' not found")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

