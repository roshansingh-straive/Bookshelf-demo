"""FastAPI server for replay and actual bookshelf recognition."""
import asyncio
import contextlib
import json
import logging
import os
from dataclasses import asdict
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from server.accuracy import OVERLAP, TILE_EDGE, configured_providers, select_profile
from server.comparison import compare_books
from server.recognition import MAX_IMAGE_BYTES, RecognitionError, run_recognition
from server.uploads import get_upload, save_upload, saved_analysis_path, upload_directory

ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "app" / "dist"
DATA_DIR = ROOT / "app" / "public" / "data"
PHOTOS_DIR = ROOT / "app" / "public" / "photos"

# Optional local configuration. Never send secret values to the browser.
env_file = ROOT / "server" / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))

app = FastAPI(title="Shelf Check API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://{host}:{port}" for host in ("localhost", "127.0.0.1") for port in (3000, 8000)],
    allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type"],
)
# One active live scan per server avoids accidentally multiplying paid crop runs.
_live_scan_lock = asyncio.Lock()


class ScanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bay_id: str = Field(pattern=r"^bay_[a-z0-9]+$", max_length=40)
    mode: Literal["replay", "live"] = "replay"
    policy: Literal["auto", "opus"] = "auto"
    upload_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")


@app.get("/api/health")
def health():
    providers = configured_providers()
    profiles, available = {}, {}
    for difficulty in ("easy", "medium", "hard"):
        try:
            profiles[difficulty] = asdict(select_profile(difficulty, live=True))
            available[difficulty] = True
        except ValueError:
            profiles[difficulty] = asdict(select_profile(difficulty))
            available[difficulty] = False
    return {
        "status": "healthy", "default_mode": "replay",
        "default_model": "Best measured setup for the shelf",
        "keys_configured": providers, "live_mode_available": any(available.values()),
        "live_available_by_difficulty": available, "profiles_by_difficulty": profiles,
        "upload_analysis_available": providers["anthropic"],
        "accuracy_settings": {"tile_edge": TILE_EDGE, "overlap": OVERLAP, "independent_rotated_verification": True},
        "disclaimer": "Simulated store data",
    }


@app.get("/api/store")
def get_store():
    path = DATA_DIR / "store.json"
    if not path.exists():
        raise HTTPException(404, "Store data not generated")
    return json.loads(path.read_text(encoding="utf-8"))


def get_bay(bay_id):
    store = get_store()
    bay = next((b for b in store["bays"] if b["id"] == bay_id and b.get("scannable")), None)
    if bay is None:
        raise HTTPException(404, "Scannable bay not found")
    return store, bay


@app.get("/api/scan/{bay_id}")
def get_bay_scan(bay_id: str):
    get_bay(bay_id)
    path = DATA_DIR / "scans" / f"{bay_id}.json"
    if not path.exists():
        raise HTTPException(404, "Saved scan not generated")
    return json.loads(path.read_text(encoding="utf-8"))


@app.post("/api/uploads", status_code=201)
async def upload_photo(request: Request, filename: str = "shelf-photo"):
    # Read incrementally so a misleading Content-Length cannot bypass the limit.
    chunks, total = [], 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > MAX_IMAGE_BYTES:
            raise HTTPException(413, "Choose an image smaller than 20 MB.")
        chunks.append(chunk)
    return await asyncio.to_thread(save_upload, b"".join(chunks), filename)


@app.get("/api/uploads/{upload_id}")
def uploaded_photo(upload_id: str):
    return get_upload(upload_id)


@app.get("/api/uploads/{upload_id}/image")
def uploaded_image(upload_id: str):
    metadata = get_upload(upload_id)
    return FileResponse(upload_directory(upload_id) / "image", media_type=metadata["media_type"],
                        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@app.get("/api/uploads/{upload_id}/analysis/{bay_id}")
def uploaded_analysis(upload_id: str, bay_id: str):
    get_bay(bay_id)
    path = saved_analysis_path(upload_id, bay_id)
    return {"result": json.loads(path.read_text(encoding="utf-8")) if path.exists() else None}


@app.post("/api/scan/stream")
async def stream_scan(req: ScanRequest):
    store, bay = get_bay(req.bay_id)
    upload = get_upload(req.upload_id) if req.upload_id else None
    if upload and req.mode != "live":
        raise HTTPException(422, "Uploaded photos require a new analysis. Sample results cannot be used for an uploaded photo.")
    if req.mode == "replay":
        result = get_bay_scan(req.bay_id)

        async def replay_events():
            for event in (
                {"step": 0, "status": "replay", "message": "Loading a saved benchmark reply. No model call or zoom verification is performed."},
                {"step": 4, "status": "complete", "result": result},
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        return StreamingResponse(replay_events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})

    try:
        # A new photo's difficulty is unknown; its selected bay must not cause a
        # crowded upload to inherit a tidy sample photo's model configuration.
        profile = select_profile("hard", "opus", live=True) if upload else select_profile(bay.get("difficulty", "hard"), req.policy, live=True)
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc
    if _live_scan_lock.locked():
        raise HTTPException(409, "A live shelf scan is already running. Wait for it to finish or cancel it.")
    photo_path = upload_directory(req.upload_id) / "image" if upload else (PHOTOS_DIR / bay["photo"]).resolve()
    if not upload and (photo_path.parent != PHOTOS_DIR.resolve() or not photo_path.is_file()):
        raise HTTPException(404, "Shelf photograph not found")
    raw = photo_path.read_bytes()

    async def events():
        queue = asyncio.Queue()

        async def work():
            # Recheck here to close the gap between HTTP validation and stream
            # startup: a second request must fail, not queue another paid scan.
            if _live_scan_lock.locked():
                await queue.put({"status": "error", "message": "A live shelf scan is already running. No additional scan was queued."})
                return
            async with _live_scan_lock:
                try:
                    books, metadata = await run_recognition(raw, profile, queue.put)
                    await queue.put({"step": 3, "status": "comparing", "message": "Matching independently read titles to the planogram; unconfirmed titles require review."})
                    result = {"bay_id": bay["id"], "bay_code": bay["code"], "bay_name": bay["name"],
                              "photo_filename": upload["filename"] if upload else bay["photo"],
                              "photo_url": upload["photo_url"] if upload else f"/photos/{bay['photo']}",
                              "source_kind": "upload" if upload else "sample", "upload_id": req.upload_id,
                              **metadata, **compare_books(store, bay, books)}
                    if upload:
                        saved_analysis_path(req.upload_id, bay["id"]).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
                    await queue.put({"step": 4, "status": "complete", "result": result})
                except RecognitionError as exc:
                    await queue.put({"status": "error", "message": str(exc)})
                except Exception:
                    logging.getLogger(__name__).exception("Live shelf scan failed")
                    await queue.put({"status": "error", "message": "Live scan failed. Previous results are unchanged; no replay was substituted."})

        task = asyncio.create_task(work())
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=10)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                if event["status"] in {"complete", "error"}:
                    break
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


if DIST_DIR.exists():
    for folder in ("assets", "photos", "data"):
        if (DIST_DIR / folder).exists():
            app.mount(f"/{folder}", StaticFiles(directory=DIST_DIR / folder), name=folder)

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(404, "API endpoint not found")
        path = (DIST_DIR / full_path).resolve()
        if DIST_DIR.resolve() not in path.parents:
            if full_path:
                raise HTTPException(404, "File not found")
        if path.is_file():
            return FileResponse(path)
        return FileResponse(DIST_DIR / "index.html")
