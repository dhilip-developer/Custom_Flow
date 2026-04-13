"""
Agent 2: Structured Data Extractor
Standalone FastAPI application — run independently via:
    python agents/agent2_data_extractor.py
    OR
    uvicorn agents.agent2_data_extractor:app --host 0.0.0.0 --port 30496
"""
import os, sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from shared.config import load_credentials, add_cors, AGENT_PORTS
load_credentials()

from fastapi import FastAPI
from agent2_data_extractor.routes import router

app = FastAPI(
    title="Agent 2: Structured Data Extractor",
    description="Agent dedicated to ripping out exact Key-Value pairs based on document type.",
    version="4.0.0",
)

add_cors(app)
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    port = AGENT_PORTS["agent2_data_extractor"]
    print(f"Starting Agent 2 (Data Extractor) on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
