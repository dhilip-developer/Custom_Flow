"""
Agent 0: Email Document Retriever
Standalone FastAPI application — run independently via:
    python agents/agent0_email_scanner.py
    OR
    uvicorn agents.agent0_email_scanner:app --host 0.0.0.0 --port 30499
"""
import os, sys

# Ensure project root is on sys.path regardless of where this script is invoked from
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from shared.config import load_credentials, add_cors, AGENT_PORTS
load_credentials()

from fastapi import FastAPI
from agent0_email_scanner.routes import router

app = FastAPI(
    title="Agent 0: Email Document Retriever",
    description=(
        "Agent that scans Gmail and Zoho inboxes for emails FROM a specified sender "
        "and returns all document attachments as base64-encoded content, ready for "
        "the downstream Agents 1 → 2 → 3 → 4 pipeline."
    ),
    version="1.0.0",
)

add_cors(app)
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    port = AGENT_PORTS["agent0_email_scanner"]
    print(f"Starting Agent 0 (Email Scanner) on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
