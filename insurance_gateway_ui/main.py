import os, sys
from pathlib import Path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routes import ui_router

app = FastAPI(title="Insurance UI Gateway")

# We must dynamically grab the templates/static from the shared_app folder
static_dir = Path(_PROJECT_ROOT) / "app" / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(ui_router)

if __name__ == "__main__":
    import uvicorn
    print("Starting Insurance Gateway on port 30492...")
    uvicorn.run(app, host="0.0.0.0", port=30492)
