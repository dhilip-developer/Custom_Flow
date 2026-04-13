"""
Agent 5: Document Cross-Verifier
Standalone FastAPI application — run independently via:
    python agents/agent5_cross_verifier.py
    OR
    uvicorn agents.agent5_cross_verifier:app --host 0.0.0.0 --port 30494
"""
import os, sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from shared.config import load_credentials, add_cors, AGENT_PORTS
load_credentials()

from fastapi import FastAPI
from agent5_cross_verifier.routes import router

app = FastAPI(
    title="Agent 5: Document Cross-Verifier",
    description=(
        "Agent that cross-verifies field-level consistency across BOL, Invoice, "
        "Packing List, Freight Certificate, and Insurance Certificate to confirm "
        "all documents belong to the same shipment."
    ),
    version="1.0.0",
)

add_cors(app)
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    port = AGENT_PORTS["agent5_cross_verifier"]
    print(f"Starting Agent 5 (Cross Verifier) on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
