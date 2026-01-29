"""
Agent core module - the brain of the Computer Use Agent.
Implements OBSERVE → DECIDE → EXECUTE → VERIFY → ESCALATE state machine.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from PIL import Image

from ..execution.executor import Executor, ExecutionResult
from ..execution.desktop_controller import DesktopController
from ..llm.base import LLMClient
from ..schemas.actions import Action, DoneAction, FailAction
from ..schemas.tasks import Task, TaskResult
from .state import AgentState, StepRecord
from .planner import Planner, PlannerInput, TextState, parse_actions
from ..perception.ocr import contains_goal_indicators


class Agent:
    """
    Accessibility-first agent with local OCR & Multi-step planning.
    Uses text-only planner by default, vision only as fallback.
    """

    def __init__(
        self,
        planner: Planner,
        executor: DesktopController,
        vision_llm: Optional[LLMClient] = None,
        runs_dir: str = "runs",
    ):
        self._planner = planner
        self._executor = executor
        self._vision = vision_llm
        self._runs_dir = Path(runs_dir)

    def run(self, task: Task) -> TaskResult:
        """Execute task using state machine."""
        run_dir = self._runs_dir / task.run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        state = AgentState(goal=task.goal, max_steps=task.max_steps)
        state.mark_running()
        last_action_str = ""
        verified = True

        try:
            for step in range(1, task.max_steps + 1):
                # === 1. OBSERVE & LOCAL VALIDATION (Save LLM call) ===
                screenshot = self._executor.screenshot()
                ss_path = run_dir / f"step_{step:03d}.png"
                screenshot.save(ss_path)
                
                # Check if goal reached LOCALLY using OCR (saves 1 credit)
                if contains_goal_indicators(screenshot, task.goal):
                    msg = f"Goal reached (locally verified via OCR)"
                    done = DoneAction(final_answer=msg, reason="OCR Match")
                    self._record(state, step, done, True, ss_path)
                    state.mark_completed(msg)
                    return TaskResult(success=True, steps_taken=step,
                                      final_answer=msg, run_id=task.run_id)

                text_state = TextState(**self._executor.get_text_state())

                # === 2. DECIDE (Multi-step sequence from 1 LLM call) ===
                actions = self._decide_sequence(task.goal, step, last_action_str, verified, text_state)

                # Execute the sequence of steps
                for i, action in enumerate(actions):
                    sub_step_id = f"{step}.{i+1}"
                    
                    # Terminal check
                    if isinstance(action, DoneAction):
                        state.mark_completed(action.final_answer)
                        return TaskResult(success=True, steps_taken=step,
                                          final_answer=action.final_answer, run_id=task.run_id)
                    if isinstance(action, FailAction):
                        state.mark_failed(action.error)
                        return TaskResult(success=False, steps_taken=step,
                                          error=action.error, run_id=task.run_id)

                    # === 3. EXECUTE ===
                    result = self._executor.execute(action)
                    last_action_str = f"{action.type}({getattr(action, 'key', getattr(action, 'text', ''))})"
                    
                    # Update verification for the last action in sequence
                    if i == len(actions) - 1:
                        new_state = self._executor.get_text_state()
                        verified = self._verify(result, text_state, new_state, action)
                    
                    self._record(state, step, action, result.ok, ss_path, result.error)

                # === 4. ESCALATE (Vision fallback if stuck) ===
                if not verified and self._vision:
                    fallback_action = self._escalate(screenshot, task.goal, step)
                    if fallback_action and not isinstance(fallback_action, (DoneAction, FailAction)):
                        self._executor.execute(fallback_action)

        except Exception as e:
            state.mark_failed(str(e))
            return TaskResult(success=False, steps_taken=state.step_count,
                              error=str(e), run_id=task.run_id)

        state.mark_failed("Max steps reached")
        self._save_meta(run_dir, task, state)
        return TaskResult(success=False, steps_taken=task.max_steps,
                          error="Max steps reached", run_id=task.run_id)

    def _decide_sequence(self, goal: str, step: int, last_action: str,
                        verified: bool, text_state: TextState) -> List[Action]:
        """DECIDE phase: Get a sequence of actions from the planner."""
        inp = PlannerInput(goal=goal, step=step, last_action=last_action,
                           verification_passed=verified, text_state=text_state)
        output = self._planner.decide(inp)
        return parse_actions(output)

    def _verify(self, result: ExecutionResult, old: TextState,
                new: dict, action: Action) -> bool:
        """VERIFY phase: check if action worked (text-based)."""
        if not result.ok:
            return False
        if action.type in ["TYPE", "WAIT"]: return True
        return old.window_title != new.get("window_title", old.window_title)

    def _escalate(self, screenshot: Image.Image, goal: str, step: int) -> Optional[Action]:
        """Vision fallback."""
        try:
            return self._vision.get_next_action(
                screenshot=screenshot, goal=goal,
                history=[{"step": step, "note": "verification failed"}]
            )
        except: return None

    def _record(self, state: AgentState, step: int, action: Action,
                ok: bool, ss_path: Path, error: str = None):
        state.add_step(StepRecord(
            step=step, action_type=action.type,
            action_data=action.model_dump(), result_ok=ok,
            screenshot_path=str(ss_path), error=error
        ))

    def _save_meta(self, run_dir: Path, task: Task, state: AgentState):
        meta = {"task": task.goal, "steps": state.step_count,
                "timestamp": datetime.now().isoformat()}
        with open(run_dir / "metadata.json", "w") as f:
            json.dump(meta, f, indent=2)
