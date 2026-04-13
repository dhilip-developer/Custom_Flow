"""
Agent 3: Document Classifier & Verifier
Standalone FastAPI application.
"""
import os, sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from shared.config import load_credentials, add_cors, AGENT_PORTS
load_credentials()

from fastapi import FastAPI
from agent3_classifier.routes import router

app = FastAPI(
    title="Agent 3: Classifier & Verifier",
    description="Agent dedicated to verifying extracted structured data against document types.",
    version="4.0.0",
)

add_cors(app)
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    port = AGENT_PORTS["agent3_classifier"]
    print(f"Starting Agent 3 (Verifier) on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
