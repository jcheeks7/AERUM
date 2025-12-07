"""FastAPI backend exposing mission control APIs for the dashboard."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Ensure the src directory is importable when running directly
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from aerum.core.controller import AERUMController
from aerum.io.event_store import event_store

app = FastAPI(title="AERUM Control Dashboard")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = ROOT / "aerum" / "web"
app.mount("/ui", StaticFiles(directory=str(FRONTEND_DIR)), name="ui")

controller = AERUMController(store=event_store)


class StartMissionRequest(BaseModel):
    mission_name: str


class FaultRequest(BaseModel):
    fault_type: str
    target_agent: str
    details: Optional[dict] = None


@app.get("/")
async def serve_dashboard() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/missions")
async def list_missions():
    return controller.list_missions()


@app.post("/api/missions/start")
async def start_mission(payload: StartMissionRequest):
    success, error = controller.start_mission(payload.mission_name)
    if not success:
        raise HTTPException(status_code=400, detail=error or "Unable to start mission")
    return controller.get_mission_status()


@app.post("/api/missions/pause")
async def pause_mission():
    success, error = controller.pause_mission()
    if not success:
        raise HTTPException(status_code=400, detail=error or "Unable to pause mission")
    return controller.get_mission_status()


@app.post("/api/missions/resume")
async def resume_mission():
    success, error = controller.resume_mission()
    if not success:
        raise HTTPException(status_code=400, detail=error or "Unable to resume mission")
    return controller.get_mission_status()


@app.post("/api/missions/abort")
async def abort_mission():
    success, error = controller.abort_mission("Manual abort from dashboard")
    if not success:
        raise HTTPException(status_code=400, detail=error or "Unable to abort mission")
    return controller.get_mission_status()


@app.post("/api/faults/inject")
async def inject_fault(payload: FaultRequest):
    success, error = controller.inject_fault(payload.fault_type, payload.target_agent, payload.details)
    if not success:
        raise HTTPException(status_code=400, detail=error or "Unable to inject fault")
    return {"status": "ok"}


@app.get("/api/status")
async def mission_status():
    return controller.get_mission_status()


@app.get("/api/agents")
async def agents_state():
    return controller.get_agents_state()


@app.get("/api/logs")
async def recent_logs(limit: int = 200):
    return controller.get_recent_logs(limit=limit)


@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    queue = event_store.subscribe()
    try:
        while True:
            event = await asyncio.get_running_loop().run_in_executor(None, queue.get)
            await websocket.send_json(event)
    except WebSocketDisconnect:
        event_store.unsubscribe(queue)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.server:app", host="0.0.0.0", port=8000, reload=False)
