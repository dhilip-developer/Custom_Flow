"""
Agent 4: Freight Certificate Detector
Standalone FastAPI application — run independently via:
    python agents/agent4_freight_cert.py
    OR
    uvicorn agents.agent4_freight_cert:app --host 0.0.0.0 --port 30495
"""
import os, sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from shared.config import load_credentials, add_cors, AGENT_PORTS
load_credentials()

from fastapi import FastAPI
from agent4_freight_cert.routes import router

app = FastAPI(
    title="Agent 4: Freight Certificate Detector",
    description=(
        "Agent that analyses Invoice, Packing List, and BOL text to determine whether "
        "a Freight Certificate is required, based on Incoterms (FOB, EXW, FCA, CNF, CIF) "
        "and freight charge/payment status."
    ),
    version="1.0.0",
)

add_cors(app)
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    port = AGENT_PORTS["agent4_freight_cert"]
    print(f"Starting Agent 4 (Freight Cert Detector) on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
