"""
Agent 1: OCR Text Extractor
Standalone FastAPI application — run independently via:
    python agents/agent1_ocr_extractor.py
    OR
    uvicorn agents.agent1_ocr_extractor:app --host 0.0.0.0 --port 30498
"""
import os, sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from shared.config import load_credentials, add_cors, AGENT_PORTS
load_credentials()

from fastapi import FastAPI
from agent1_ocr_extractor.routes import router

app = FastAPI(
    title="Agent 1: OCR Extractor",
    description="Agent dedicated solely to converting physical PDFs/Images into raw plaintext.",
    version="3.0.0",
)

add_cors(app)
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    port = AGENT_PORTS["agent1_ocr_extractor"]
    print(f"Starting Agent 1 (OCR Extractor) on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
