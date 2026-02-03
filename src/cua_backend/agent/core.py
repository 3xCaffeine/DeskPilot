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
from ..schemas.actions import Action, DoneAction, FailAction, WaitAction
from ..schemas.tasks import Task, TaskResult
from .state import AgentState, StepRecord
from .planner import Planner, PlannerInput, TextState, parse_actions


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
        self._history: List[str] = [] # Track actions and outcomes 

    def run(self, task: Task) -> TaskResult:
        """Execute task using state machine."""
        run_dir = self._runs_dir / task.run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        state = AgentState(goal=task.goal, max_steps=task.max_steps)
        state.mark_running()
        last_expected_title = None
        success_markers = []
        verified = True # Base state for first step

        try:
            for step in range(1, task.max_steps + 1):
                # === 1. OBSERVE & LOCAL VALIDATION (Save LLM call) ===
                screenshot = self._executor.screenshot()
                ss_path = run_dir / f"step_{step:03d}.png"
                screenshot.save(ss_path)
                
                # === 0. CHECK COMPLETION (Locally) ===
                current_state = self._executor.get_text_state()
                current_title = current_state.get("window_title", "").lower()
                
                # INTERMEDIATE GUARD: Don't auto-finish on search engines if we are deep-diving
                is_search_engine = any(s in current_title for s in ["google", "bing", "search"])
                
                # We check for completion ONLY if we have markers to look for AND NOT on a search engine
                if not is_search_engine and last_expected_title and last_expected_title.lower() in current_title:
                    from ..perception.ocr import get_text_from_image
                    page_text = get_text_from_image(screenshot).lower()
                    
                    # Parse indicators string to list
                    markers = [m.strip() for m in success_markers.split(",")] if success_markers else []
                    
                    # If markers exist on screen, we are truly DONE
                    if markers and any(m.lower() in page_text for m in markers):
                        msg = f"Goal reached (Verified: Title='{last_expected_title}', Content={success_markers})"
                        done = DoneAction(final_answer=msg, reason="Anchor + Indicator Match")
                        self._record(state, step, done, True, ss_path)
                        state.mark_completed(msg)
                        return TaskResult(success=True, steps_taken=step, final_answer=msg, run_id=task.run_id)

                text_state = TextState(**self._executor.get_text_state())

                # === 2. DECIDE (Multi-step sequence from 1 LLM call) ===
                actions, expected_title, indicators, sub_goals = self._decide_sequence(task.goal, step, self._history, text_state)
                last_expected_title = expected_title
                success_markers = indicators
                
                # Tracking sub-goals in history for the AI
                if sub_goals:
                    self._history.append(f"Checklist: {sub_goals}")

                # === 3. EXECUTE & VALIDATE (Retry loop) ===
                for attempt in range(2): # Up to 2 retries locally
                    sequence_ok = True
                    for i, action in enumerate(actions):
                        # Execute individual action
                        result = self._executor.execute(action)
                        action_str = f"{action.type}({getattr(action, 'key', getattr(action, 'text', ''))})"
                        self._record(state, step, action, result.ok, ss_path, result.error)
                        
                        # Immediate Success/Fail signal from AI
                        if isinstance(action, DoneAction):
                            state.mark_completed(action.final_answer)
                            return TaskResult(success=True, steps_taken=step, final_answer=action.final_answer, run_id=task.run_id)
                        if isinstance(action, FailAction):
                            state.mark_failed(action.error)
                            return TaskResult(success=False, steps_taken=step, error=action.error, run_id=task.run_id)

                    # Post-sequence Local Validation (The Anchor) with Polling
                    anchor_found = False
                    print(f"⌛ Waiting for anchor: '{expected_title}'...")
                    for _ in range(5): # Poll for up to 5 seconds
                        current_state = self._executor.get_text_state()
                        current_title = current_state.get("window_title", "").lower()
                        if expected_title.lower() in current_title:
                            anchor_found = True
                            break
                        import time
                        time.sleep(1)
                    
                    if anchor_found:
                        # Step sequence worked (Anchor matched)
                        is_search_engine = any(s in current_title for s in ["google", "bing", "search"])
                        
                        if not is_search_engine:
                            # Potential Full Completion (Soft check)
                            from ..perception.ocr import get_text_from_image
                            page_text = get_text_from_image(screenshot).lower()
                            markers = [m.strip() for m in success_markers.split(",")] if success_markers else []
                            
                            if markers and any(m.lower() in page_text for m in markers):
                                self._history.append(f"Step {step}: {actions} -> SUCCESS (Goal Indicators found)")
                                verified = True
                                break 
                        
                        # If we get here, it's either a search engine OR anchor matched but no markers found.
                        # Either way, the SEQUENCE worked, so we don't retry.
                        self._history.append(f"Step {step}: {actions} -> STEP SUCCESS (Anchor matched: '{current_title}')")
                        verified = True
                        break
                    else:
                        # Hard Mismatch (Retry sequence)
                        print(f"⚠️ Anchor mismatch: Expected '{expected_title}', got '{current_title}'")
                        self._history.append(f"Step {step}: {actions} -> FAIL (Anchor mismatch)")
                        verified = False
                        self._executor.execute(WaitAction(seconds=1.5))

                # === 4. ESCALATE (Vision fallback if LOCAL retries failed) ===
                if not verified and self._vision:
                    current_state = self._executor.get_text_state()
                    current_title = current_state.get("window_title", "unknown")
                    
                    print(f"🚨 Local validation failed. Escalating to Vision...")
                    print(f"   Context: Expected '{expected_title}', found '{current_title}'")
                    
                    fallback_action = self._escalate(
                        screenshot, task.goal, step, 
                        expected=expected_title, found=current_title
                    )
                    
                    if fallback_action and not isinstance(fallback_action, (DoneAction, FailAction)):
                        print(f"📸 Vision suggested: {fallback_action.type}")
                        self._executor.execute(fallback_action)
                        # Re-verify after vision action
                        final_state = self._executor.get_text_state()
                        verified = expected_title.lower() in final_state.get("window_title", "").lower()

        except Exception as e:
            state.mark_failed(str(e))
            return TaskResult(success=False, steps_taken=state.step_count,
                              error=str(e), run_id=task.run_id)

        state.mark_failed("Max steps reached")
        self._save_meta(run_dir, task, state)
        return TaskResult(success=False, steps_taken=task.max_steps,
                          error="Max steps reached", run_id=task.run_id)

    def _decide_sequence(self, goal: str, step: int, history: List[str],
                        text_state: TextState) -> tuple[List[Action], str, str, str]:
        """DECIDE phase: Get a sequence of actions, expected title, success markers, and sub_goals."""
        inp = PlannerInput(goal=goal, step=step, history=history, text_state=text_state)
        output = self._planner.decide(inp)
        return parse_actions(output), output.expected_window_title, output.success_indicators, output.sub_goals


    def _escalate(self, screenshot: Image.Image, goal: str, step: int, 
                  expected: str = None, found: str = None) -> Optional[Action]:
        """Vision fallback with targeted context."""
        try:
            context = f"Local verification failed. Expected window title: '{expected}', but found: '{found}'."
            return self._vision.get_next_action(
                screenshot=screenshot, goal=goal,
                history=[{"step": step, "note": context}]
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
