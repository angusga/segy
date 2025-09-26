from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
import os
import asyncio

from .segy_processing import (
    save_and_parse_segy,
    get_segy_metadata,
    get_inline_slice,
    get_crossline_slice,
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

app = FastAPI(title="Oilfield 3D Integrated Viewer Backend")

# CORS for local development and simple static hosting of frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory state for drill trajectory and clients
drill_clients: List[WebSocket] = []
drill_state: Dict[str, Any] = {
    "path": [],  # list of [lon, lat, height] points
    "bit": None,  # current bit position [lon, lat, height]
    "md": 0.0,    # measured depth
}


@app.post("/api/segy/upload")
async def upload_segy(file: UploadFile = File(...)):
    try:
        saved_path = save_and_parse_segy(file, DATA_DIR)
        meta = get_segy_metadata(saved_path)
        return JSONResponse({"status": "ok", "path": saved_path, "metadata": meta})
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})


@app.get("/api/segy/metadata")
async def segy_metadata():
    # We assume last uploaded file named 'latest.sgy' in DATA_DIR
    segy_path = os.path.join(DATA_DIR, "latest.sgy")
    if not os.path.exists(segy_path):
        return JSONResponse(status_code=404, content={"status": "error", "message": "No SEGY uploaded"})
    meta = get_segy_metadata(segy_path)
    return JSONResponse({"status": "ok", "metadata": meta})


@app.get("/api/segy/slice/inline/{iline}")
async def segy_inline_slice(iline: int):
    segy_path = os.path.join(DATA_DIR, "latest.sgy")
    if not os.path.exists(segy_path):
        return JSONResponse(status_code=404, content={"status": "error", "message": "No SEGY uploaded"})
    data = get_inline_slice(segy_path, iline)
    return JSONResponse({"status": "ok", "iline": iline, "data": data})


@app.get("/api/segy/slice/crossline/{xline}")
async def segy_crossline_slice(xline: int):
    segy_path = os.path.join(DATA_DIR, "latest.sgy")
    if not os.path.exists(segy_path):
        return JSONResponse(status_code=404, content={"status": "error", "message": "No SEGY uploaded"})
    data = get_crossline_slice(segy_path, xline)
    return JSONResponse({"status": "ok", "xline": xline, "data": data})


@app.post("/api/drill/update")
async def update_drill(payload: Dict[str, Any]):
    """
    Accepts:
    {
      "bit": [lon, lat, height],
      "md": float,
      "path": [[lon, lat, height], ...]  # optional, full or partial trajectory
    }
    """
    global drill_state
    bit = payload.get("bit")
    md = payload.get("md")
    path = payload.get("path")

    if bit is not None:
        drill_state["bit"] = bit
    if md is not None:
        drill_state["md"] = md
    if path:
        drill_state["path"] = path

    await broadcast_drill_state()
    return JSONResponse({"status": "ok", "drill_state": drill_state})


async def broadcast_drill_state():
    if not drill_clients:
        return
    message = {"type": "drill_state", "payload": drill_state}
    stale_clients = []
    for ws in drill_clients:
        try:
            await ws.send_json(message)
        except Exception:
            stale_clients.append(ws)
    for ws in stale_clients:
        try:
            drill_clients.remove(ws)
        except ValueError:
            pass


@app.websocket("/ws/drill")
async def ws_drill(websocket: WebSocket):
    await websocket.accept()
    drill_clients.append(websocket)

    # Send initial state
    await websocket.send_json({"type": "drill_state", "payload": drill_state})

    try:
        while True:
            # Optional: receive client messages (e.g., pings or subscriptions)
            # Keep the connection alive
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        try:
            drill_clients.remove(websocket)
        except ValueError:
            pass


# Simple health check
@app.get("/health")
async def health():
    return {"status": "ok"}