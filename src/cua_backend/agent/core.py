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
        consecutive_failures = 0  # Track stuck loops

        try:
            for step in range(1, task.max_steps + 1):
                # === 1. OBSERVE & LOCAL VALIDATION (Save LLM call) ===
                screenshot = self._executor.screenshot()
                ss_path = run_dir / f"step_{step:03d}.png"
                screenshot.save(ss_path)
                
                # === 0. CHECK COMPLETION (Locally) ===
                current_state = self._executor.get_text_state()
                current_title = current_state.get("window_title", "").lower()
                current_url = current_state.get("current_url", "")
                is_browser = current_state.get("is_browser", False)
                
                # Use URL for verification if in browser (more reliable than title)
                verification_key = current_url if is_browser else current_title
                
                # COMPLETION CHECK: Only mark done if we have BOTH anchor match AND success indicators
                # This prevents premature completion on intermediate pages (like Amazon homepage before searching)
                if last_expected_title and last_expected_title.lower() in verification_key.lower():
                    # Parse indicators string to list
                    markers = [m.strip() for m in success_markers.split(",")] if success_markers else []
                    
                    # STRICT POLICY: Must have success_indicators AND find them on screen
                    if markers:
                        from ..perception.ocr import get_text_from_image
                        page_text = get_text_from_image(screenshot).lower()
                        
                        if any(m.lower() in page_text for m in markers):
                            msg = f"Goal reached (Verified: {'URL' if is_browser else 'Title'}='{last_expected_title}', Content={success_markers})"
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
                        print(f"   🎯 Executing: {action.type} - {action}")
                        result = self._executor.execute(action)
                        print(f"   {'✅' if result.ok else '❌'} Result: ok={result.ok}, error={result.error}")
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
                    for poll_attempt in range(5): # Poll for up to 5 seconds
                        current_state = self._executor.get_text_state()
                        current_title = current_state.get("window_title", "").lower()
                        current_url = current_state.get("current_url", "")
                        is_browser = current_state.get("is_browser", False)
                        
                        print(f"   Poll {poll_attempt + 1}: title='{current_title}', url='{current_url}', is_browser={is_browser}")
                        
                        if expected_title.lower() in current_title:
                            anchor_found = True
                            break
                        # Also check URL if in browser
                        if is_browser and current_url and expected_title.lower() in current_url.lower():
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
                        consecutive_failures = 0  # Reset on success
                        break
                    else:
                        # Hard Mismatch (Retry sequence)
                        print(f"⚠️ Anchor mismatch: Expected '{expected_title}', got '{current_title}'")
                        self._history.append(f"Step {step}: {actions} -> FAIL (Anchor mismatch: expected '{expected_title}' got '{current_title}')")
                        verified = False
                        consecutive_failures += 1
                        self._executor.execute(WaitAction(seconds=1.5))

                # === 4. ESCALATE (CDP → Vision fallback if LOCAL retries failed) ===
                if not verified:
                    # Track failures - if stuck in loop, add urgent recovery hint to history
                    if consecutive_failures >= 2:
                        print(f"⚠️ LOOP DETECTED: {consecutive_failures} consecutive failures")
                        recovery_hint = f"URGENT: Stuck in loop after {consecutive_failures} failures. current_url='{current_url if is_browser else 'N/A'}'. Use BROWSER_NAVIGATE or different approach!"
                        self._history.append(recovery_hint)
                    
                    current_state = self._executor.get_text_state()
                    current_title = current_state.get("window_title", "unknown")
                    current_url = current_state.get("current_url", "")
                    is_browser = current_state.get("is_browser", False)
                    
                    # Try CDP verification first if in browser
                    if is_browser and current_url:
                        print(f"🔍 Trying CDP verification...")
                        # Check if URL matches expected pattern
                        if expected_title.lower() in current_url.lower():
                            print(f"   ✅ CDP verified: URL contains '{expected_title}'")
                            verified = True
                            self._history.append(f"Step {step}: {actions} -> OK (CDP URL match)")
                        else:
                            # Try checking page content via browser state
                            browser_state = self._executor.get_browser_state()
                            if browser_state and browser_state.visible_text:
                                if any(marker.lower() in browser_state.visible_text.lower() 
                                       for marker in success_markers.split(",") if marker.strip()):
                                    print(f"   ✅ CDP verified: Content markers found")
                                    verified = True
                                    self._history.append(f"Step {step}: {actions} -> OK (CDP content match)")
                    
                    # Force vision if stuck in loop (even if CDP thinks it's OK - might be popup/modal)
                    if consecutive_failures >= 3 and self._vision:
                        print(f"🚨 STUCK IN LOOP - Forcing vision escalation...")
                        verified = False  # Override CDP verification
                    
                    # Fall back to vision if CDP didn't verify OR we're stuck
                    if not verified and self._vision:
                        print(f"🚨 Local validation failed. Escalating to Vision...")
                        print(f"   Context: Expected '{expected_title}', found '{current_title if not is_browser else current_url}'")
                        
                        fallback_action = self._escalate(
                            screenshot, task.goal, step, 
                            expected=expected_title, found=current_title
                        )
                        
                        if fallback_action and not isinstance(fallback_action, (DoneAction, FailAction)):
                            print(f"📸 Vision suggested: {fallback_action.type}")
                            self._executor.execute(fallback_action)
                            # Re-verify after vision action
                            final_state = self._executor.get_text_state()
                            if final_state.get("is_browser"):
                                verified = expected_title.lower() in final_state.get("current_url", "").lower()
                            else:
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
        if not self._vision:
            print(f"   ⚠️ Vision LLM not configured, cannot escalate")
            return None
            
        try:
            context = f"Local verification failed. Expected window title: '{expected}', but found: '{found}'."
            action = self._vision.get_next_action(
                screenshot=screenshot, goal=goal,
                history=[{"step": step, "note": context}]
            )
            print(f"   📸 Vision returned: {action.type if action else 'None'}")
            return action
        except Exception as e:
            print(f"   ❌ Vision escalation error: {e}")
            return None

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
