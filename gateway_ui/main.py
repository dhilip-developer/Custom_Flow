"""
Gateway: CustomsFlow Agent Gateway (UI Server)
Standalone FastAPI application — run independently via:
    python agents/gateway.py
    OR
    uvicorn agents.gateway:app --host 0.0.0.0 --port 30493
"""
import os, sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from shared.config import load_credentials, add_cors, AGENT_PORTS, PROJECT_ROOT
load_credentials()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="CustomsFlow Agent Gateway",
    description="Master Gateway connecting to the independent Document Agents.",
    version="2.0.0",
)

add_cors(app)

# Serve the frontend UI
static_dir = os.path.join(PROJECT_ROOT, "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/ui", StaticFiles(directory=static_dir, html=True), name="ui")


from fastapi.responses import RedirectResponse

@app.get("/", tags=["Gateway Status"])
def read_root():
    """Redirect to the Frontend UI."""
    return RedirectResponse(url="/ui")


if __name__ == "__main__":
    import uvicorn
    port = AGENT_PORTS["gateway"]
    print(f"Starting Gateway (UI) on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
