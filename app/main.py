"""
FastAPI application factory for the Insurance Agent.
"""
 
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from shared.insurance_app.routes import ui_router, agent1_router, agent2_router

# Main App
app = FastAPI(
    title="CustomsFlow Meta Framework",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Agent 1 API Sub-Application
agent1_app = FastAPI(
    title="Agent 1: Requirement Detector API",
    description="Determines if an Insurance Certificate is required.",
    version="2.1.0",
    docs_url="/docs"
)
agent1_app.include_router(agent1_router)

# Agent 2 API Sub-Application
agent2_app = FastAPI(
    title="Agent 2: BOL Extractor API",
    description="Extracts 13 point JSON from Bill of Lading text.",
    version="2.1.0",
    docs_url="/docs"
)
agent2_app.include_router(agent2_router)

# Static files (CSS / JS)
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Mount Sub-Apps to expose APIs separately
app.mount("/api/agent1", agent1_app)
app.mount("/api/agent2", agent2_app)

# Include UI Routes to base app
app.include_router(ui_router)
