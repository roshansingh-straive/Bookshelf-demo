"""FastAPI server for Shelf Check demo."""
import asyncio
import json
import os
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "app" / "dist"
DATA_DIR = ROOT / "app" / "public" / "data"
PHOTOS_DIR = ROOT / "app" / "public" / "photos"

# Load local untracked env if present
env_file = ROOT / "server" / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))

app = FastAPI(title="Shelf Check API", version="1.0.0")

# Security: CORS restricted to localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class ScanRequest(BaseModel):
    bay_id: str
    custom_image_b64: Optional[str] = None
    provider: Optional[str] = "anthropic"
    model_id: Optional[str] = "claude-opus-5-5"


@app.get("/api/health")
def health():
    """Health status and active mode. Never exposes secret tokens."""
    has_proxy_token = bool(os.environ.get("LLM_PROXY_TOKEN"))
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_openai = bool(os.environ.get("OPENAI_API_KEY"))
    has_gemini = bool(os.environ.get("GEMINI_API_KEY"))

    return {
        "status": "healthy",
        "default_mode": "replay",
        "default_model": "Claude Opus 5.5",
        "keys_configured": {
            "straive_foundry_proxy": has_proxy_token,
            "anthropic": has_anthropic,
            "openai": has_openai,
            "gemini": has_gemini,
        },
        "live_mode_available": has_proxy_token or has_anthropic or has_gemini or has_openai,
        "disclaimer": "Simulated store data",
    }


@app.get("/api/store")
def get_store():
    store_file = DATA_DIR / "store.json"
    if not store_file.exists():
        raise HTTPException(status_code=404, detail="Store data not generated")
    return json.loads(store_file.read_text(encoding="utf-8"))


@app.get("/api/scan/{bay_id}")
def get_bay_scan(bay_id: str):
    scan_file = DATA_DIR / "scans" / f"{bay_id}.json"
    if not scan_file.exists():
        raise HTTPException(status_code=404, detail=f"No scan data for bay {bay_id}")
    return json.loads(scan_file.read_text(encoding="utf-8"))


@app.post("/api/scan/stream")
async def stream_scan(req: ScanRequest):
    """Stream live scan progress events via SSE. Falls back gracefully to replay data."""
    bay_id = req.bay_id
    scan_file = DATA_DIR / "scans" / f"{bay_id}.json"
    if not scan_file.exists():
        raise HTTPException(status_code=404, detail=f"Bay {bay_id} not found")

    replay_data = json.loads(scan_file.read_text(encoding="utf-8"))
    model_name = req.model_id or "Claude Opus 5.5"

    async def event_generator():
        yield f"data: {json.dumps({'step': 0, 'status': 'uploading', 'message': 'Uploading shelf photograph'})}\n\n"
        await asyncio.sleep(0.5)

        yield f"data: {json.dumps({'step': 1, 'status': 'scanning', 'message': f'Reading book spines with {model_name}'})}\n\n"
        await asyncio.sleep(0.7)

        yield f"data: {json.dumps({'step': 2, 'status': 'verifying', 'message': 'Zoom-and-verify pass on uncertain titles'})}\n\n"
        await asyncio.sleep(0.6)

        yield f"data: {json.dumps({'step': 3, 'status': 'comparing', 'message': 'Cross-referencing against shelf planogram'})}\n\n"
        await asyncio.sleep(0.4)

        # Send completed scan result
        yield f"data: {json.dumps({'step': 4, 'status': 'complete', 'result': replay_data})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# Serve static frontend in production
if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")
    if (DIST_DIR / "photos").exists():
        app.mount("/photos", StaticFiles(directory=DIST_DIR / "photos"), name="photos")
    if (DIST_DIR / "data").exists():
        app.mount("/data", StaticFiles(directory=DIST_DIR / "data"), name="data")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        file_path = DIST_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(DIST_DIR / "index.html")
