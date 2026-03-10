"""DeskPilot API server."""

import json
import os
import random
import asyncio
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from .schemas import (
    TaskCreateRequest, TaskCreateResponse, TaskSummary,
    RandomTaskResponse, ConfigResponse, ConfigUpdateRequest,
    StepEvent,
)
from .task_runner import TaskRunner

app = FastAPI(title="DeskPilot API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory state
_runners: Dict[str, TaskRunner] = {}
_config = {
    "default_model": "openrouter/google/gemini-2.0-flash-001",
    "default_max_steps": 10,
}

AVAILABLE_MODELS = [
    "openrouter/google/gemini-2.0-flash-001",
    "gemini/gemini-2.5-flash",
    "openrouter/anthropic/claude-3-haiku",
]

RANDOM_TASKS_PATH = Path(__file__).resolve().parents[3] / "configs" / "random_tasks.json"
RUNS_DIR = Path(__file__).resolve().parents[3] / "runs"
SETTINGS_PATH = Path(__file__).resolve().parents[3] / "configs" / "settings.json"


def _load_saved_settings():
    """Load persisted settings and apply env vars."""
    if SETTINGS_PATH.exists():
        try:
            data = json.loads(SETTINGS_PATH.read_text())
            if data.get("openrouter_api_key"):
                os.environ["OPENROUTER_API_KEY"] = data["openrouter_api_key"]
            if data.get("gemini_api_key"):
                os.environ["GEMINI_API_KEY"] = data["gemini_api_key"]
            if data.get("default_model"):
                _config["default_model"] = data["default_model"]
            if data.get("default_max_steps"):
                _config["default_max_steps"] = data["default_max_steps"]
        except Exception:
            pass


_load_saved_settings()


# ── Tasks ──

@app.post("/api/tasks", response_model=TaskCreateResponse)
def create_task(req: TaskCreateRequest):
    from datetime import datetime
    task_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    runner = TaskRunner(
        task_id=task_id,
        goal=req.goal,
        model=req.model,
        max_steps=req.max_steps,
    )
    _runners[task_id] = runner
    runner.start()

    return TaskCreateResponse(task_id=task_id, goal=req.goal)


@app.get("/api/tasks", response_model=list[TaskSummary])
def list_tasks():
    results = []

    # From in-memory runners
    for tid, r in _runners.items():
        results.append(TaskSummary(
            task_id=tid, goal=r.goal, status=r.status,
            model=r.model,
            steps_taken=len([e for e in r.events if e.event_type == "step"]),
            final_answer=r.final_answer, error=r.error,
            created_at=r.created_at,
        ))

    # From disk (past runs not in memory)
    if RUNS_DIR.exists():
        for run_dir in sorted(RUNS_DIR.iterdir(), reverse=True):
            meta_file = run_dir / "metadata.json"
            if run_dir.name not in _runners and meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text())
                    results.append(TaskSummary(
                        task_id=run_dir.name,
                        goal=meta.get("goal", ""),
                        status=meta.get("status", "unknown"),
                        model=meta.get("model", ""),
                        steps_taken=meta.get("steps_taken", 0),
                        final_answer=meta.get("final_answer"),
                        error=meta.get("error"),
                        created_at=meta.get("created_at", ""),
                    ))
                except Exception:
                    pass

    return results


@app.get("/api/tasks/{task_id}/steps/{step_num}/screenshot")
def get_screenshot(task_id: str, step_num: int):
    path = RUNS_DIR / task_id / f"step_{step_num:03d}.png"
    if not path.exists():
        raise HTTPException(404, "Screenshot not found")
    return FileResponse(path, media_type="image/png")


# ── WebSocket ──

@app.websocket("/ws/tasks/{task_id}")
async def task_ws(ws: WebSocket, task_id: str):
    await ws.accept()
    runner = _runners.get(task_id)
    if not runner:
        await ws.send_json({"event_type": "failed", "error": "Task not found"})
        await ws.close()
        return

    # Replay past events to late-joining clients
    for event in runner.events:
        await ws.send_json(event.model_dump())

    async def _stream():
        """Push step events from the runner queue to the client."""
        while runner.status in ("queued", "running"):
            try:
                event = await asyncio.to_thread(runner.event_queue.get, timeout=1.0)
                await ws.send_json(event.model_dump())
                if event.event_type in ("completed", "failed", "cancelled"):
                    return
            except Exception:
                continue

    async def _receive():
        """Listen for cancel messages from the client."""
        try:
            async for msg in ws.iter_json():
                if isinstance(msg, dict) and msg.get("action") == "cancel":
                    runner.cancel()
                    return
        except Exception:
            pass

    stream_task = asyncio.create_task(_stream())
    recv_task = asyncio.create_task(_receive())
    try:
        done, pending = await asyncio.wait(
            [stream_task, recv_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in pending:
            t.cancel()
    except WebSocketDisconnect:
        stream_task.cancel()
        recv_task.cancel()


# ── Random Task ──

@app.get("/api/random-task", response_model=RandomTaskResponse)
def get_random_task():
    try:
        data = json.loads(RANDOM_TASKS_PATH.read_text())
        task = random.choice(data["tasks"])
        return RandomTaskResponse(task=task)
    except Exception as e:
        raise HTTPException(500, f"Failed to load random tasks: {e}")


# ── Config ──

@app.get("/api/config", response_model=ConfigResponse)
def get_config():
    import subprocess, shutil
    docker_status = "unknown"
    if shutil.which("docker"):
        try:
            r = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Running}}", "deskpilot-desktop"],
                capture_output=True, text=True, timeout=3
            )
            docker_status = "running" if r.stdout.strip() == "true" else "stopped"
        except Exception:
            pass
    return ConfigResponse(
        default_model=_config["default_model"],
        default_max_steps=_config["default_max_steps"],
        available_models=AVAILABLE_MODELS,
        docker_status=docker_status,
        vnc_url="http://localhost:6080/vnc.html",
        openrouter_key_set=bool(os.environ.get("OPENROUTER_API_KEY")),
        gemini_key_set=bool(os.environ.get("GEMINI_API_KEY")),
    )


@app.put("/api/config")
def update_config(req: ConfigUpdateRequest):
    if req.default_model is not None:
        _config["default_model"] = req.default_model
    if req.default_max_steps is not None:
        _config["default_max_steps"] = req.default_max_steps
    # Persist to disk and update env vars
    saved: dict = {}
    if SETTINGS_PATH.exists():
        try:
            saved = json.loads(SETTINGS_PATH.read_text())
        except Exception:
            pass
    saved["default_model"] = _config["default_model"]
    saved["default_max_steps"] = _config["default_max_steps"]
    if req.openrouter_api_key is not None:
        val = req.openrouter_api_key.strip()
        if val:
            os.environ["OPENROUTER_API_KEY"] = val
            saved["openrouter_api_key"] = val
    if req.gemini_api_key is not None:
        val = req.gemini_api_key.strip()
        if val:
            os.environ["GEMINI_API_KEY"] = val
            saved["gemini_api_key"] = val
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(saved, indent=2))
    return {"status": "updated"}


# ── Health ──

@app.get("/api/status")
def health():
    return {"status": "ok", "runners": len(_runners)}
