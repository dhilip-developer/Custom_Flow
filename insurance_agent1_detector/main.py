import os, sys
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from fastapi import FastAPI
from app.routes import agent1_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Agent 6: Insurance Requirement Detector",
    description="Analyzes structured shipment data to check if an Insurance Certificate is globally required",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent1_router)

if __name__ == "__main__":
    import uvicorn
    print("Starting Insurance Agent 1 on port 30491...")
    uvicorn.run(app, host="0.0.0.0", port=30491)
