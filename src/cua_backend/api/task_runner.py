"""Background task runner — wraps the Agent for async API usage."""

import subprocess
import threading
import json
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import Optional

from .schemas import StepEvent


class _TaskCancelled(BaseException):
    """Raised from on_step_callback to abort the agent loop.
    Inherits BaseException so it passes through 'except Exception' in core.py."""


class TaskRunner:
    """Runs an Agent task in a background thread with event streaming."""

    def __init__(self, task_id: str, goal: str, model: str, max_steps: int):
        self.task_id = task_id
        self.goal = goal
        self.model = model
        self.max_steps = max_steps
        self.status = "queued"
        self.events: list[StepEvent] = []
        self.event_queue: Queue = Queue()
        self.cancel_flag = threading.Event()
        self.created_at = datetime.now().isoformat()
        self.final_answer: Optional[str] = None
        self.error: Optional[str] = None
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Spawn the agent in a background thread."""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        self.status = "running"
        self._cleanup_desktop()
        try:
            from ..agent import Planner, Agent
            from ..execution import DesktopController
            from ..schemas.tasks import Task

            planner = Planner()
            planner.configure(model=self.model)

            # Vision client
            vision_client = None
            if self.model.startswith("openrouter/"):
                from ..llm.openrouter_client import OpenRouterClient
                vision_client = OpenRouterClient(model=self.model)
            else:
                from ..llm.gemini_client import GeminiClient
                gemini_model = self.model.replace("gemini/", "")
                vision_client = GeminiClient(model=gemini_model)

            controller = DesktopController()
            root_dir = Path(__file__).resolve().parents[3]
            runs_dir = str(root_dir / "runs")

            agent = Agent(
                planner=planner,
                executor=controller,
                vision_llm=vision_client,
                runs_dir=runs_dir,
                on_step_callback=self._on_step,
                cancel_check=self._check_cancel,
            )

            task = Task(goal=self.goal, max_steps=self.max_steps, run_id=self.task_id)
            result = agent.run(task)

            if result.success:
                self.final_answer = result.final_answer
                self._emit(StepEvent(
                    event_type="completed", step=result.steps_taken,
                    action_type="DONE", action_detail=result.final_answer or "",
                    result_ok=True, timestamp=datetime.now().isoformat(),
                ))
                self.status = "completed"
            else:
                self.error = result.error
                self._emit(StepEvent(
                    event_type="failed", step=result.steps_taken,
                    action_type="FAIL", action_detail=result.error or "",
                    result_ok=False, error=result.error,
                    timestamp=datetime.now().isoformat(),
                ))
                self.status = "failed"

        except _TaskCancelled:
            self._emit(StepEvent(
                event_type="cancelled", step=0,
                action_type="DONE", action_detail="Cancelled by user",
                result_ok=True, timestamp=datetime.now().isoformat(),
            ))
            self.status = "cancelled"

        except Exception as e:
            self.error = str(e)
            self._emit(StepEvent(
                event_type="failed", action_type="FAIL",
                action_detail=str(e), result_ok=False, error=str(e),
                timestamp=datetime.now().isoformat(),
            ))
            self.status = "failed"

        # Save metadata
        self._save_metadata()

    def cancel(self):
        """Signal the running task to abort."""
        self.cancel_flag.set()

    def _check_cancel(self):
        """Raise _TaskCancelled if cancel has been requested."""
        if self.cancel_flag.is_set():
            raise _TaskCancelled()

    def _cleanup_desktop(self):
        """Close all open windows before starting a new task."""
        try:
            # Get list of all window IDs
            result = subprocess.run(
                ["xdotool", "search", "--onlyvisible", "--name", ""],
                capture_output=True, text=True, timeout=3
            )
            wids = result.stdout.strip().split('\n')
            for wid in wids:
                wid = wid.strip()
                if not wid:
                    continue
                # Skip the desktop itself (window name "Desktop")
                name = subprocess.run(
                    ["xdotool", "getwindowname", wid],
                    capture_output=True, text=True, timeout=2
                )
                title = name.stdout.strip().lower()
                if title in ("desktop", "xfdesktop", ""):
                    continue
                subprocess.run(["xdotool", "windowclose", wid],
                               capture_output=True, timeout=2)
            import time
            time.sleep(0.5)
        except Exception:
            pass  # Best-effort cleanup

    def _on_step(self, data: dict):
        """Callback invoked by Agent after each action."""
        if self.cancel_flag.is_set():
            raise _TaskCancelled()
        event = StepEvent(**data)
        self._emit(event)

    def _emit(self, event: StepEvent):
        self.events.append(event)
        self.event_queue.put(event)

    def _save_metadata(self):
        run_dir = Path(__file__).resolve().parents[3] / "runs" / self.task_id
        run_dir.mkdir(parents=True, exist_ok=True)
        meta = {
            "goal": self.goal,
            "model": self.model,
            "status": self.status,
            "steps_taken": len([e for e in self.events if e.event_type == "step"]),
            "final_answer": self.final_answer,
            "error": self.error,
            "created_at": self.created_at,
            "completed_at": datetime.now().isoformat(),
        }
        with open(run_dir / "metadata.json", "w") as f:
            json.dump(meta, f, indent=2)
