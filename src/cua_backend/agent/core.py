"""
Agent core module - the brain of the Computer Use Agent.
Implements the observe → think → act loop.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import Image

from ..execution.executor import Executor, ExecutionResult
from ..llm.base import LLMClient
from ..schemas.actions import Action, DoneAction, FailAction
from ..schemas.tasks import Task, TaskResult
from .state import AgentState, AgentStatus, StepRecord


class Agent:
    """
    The core agent that orchestrates the observe → think → act loop.
    
    Takes an LLM client and executor, runs tasks until completion or failure.
    Logs all runs to runs/{timestamp}/ with screenshots and metadata.
    """

    def __init__(
        self,
        llm: LLMClient,
        executor: Executor,
        runs_dir: str = "runs",
    ):
        self._llm = llm
        self._executor = executor
        self._runs_dir = Path(runs_dir)

    def run(self, task: Task) -> TaskResult:
        """
        Execute a task using the observe → think → act loop.
        
        Args:
            task: The task to execute with goal and constraints.
            
        Returns:
            TaskResult with success/failure status and details.
        """
        # Create run directory
        run_dir = self._runs_dir / task.run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # Initialize state
        state = AgentState(goal=task.goal, max_steps=task.max_steps)
        state.mark_running()

        try:
            result = self._run_loop(task, state, run_dir)
        except Exception as e:
            state.mark_failed(str(e))
            result = TaskResult(
                success=False,
                steps_taken=state.step_count,
                error=str(e),
                run_id=task.run_id,
            )

        # Save metadata
        self._save_metadata(run_dir, task, state, result)

        return result

    def _run_loop(
        self,
        task: Task,
        state: AgentState,
        run_dir: Path,
    ) -> TaskResult:
        """Main observe → think → act loop."""
        
        for step in range(1, task.max_steps + 1):
            # --- OBSERVE ---
            screenshot = self._executor.screenshot()
            screenshot_path = run_dir / f"step_{step:03d}.png"
            screenshot.save(screenshot_path)

            # --- THINK ---
            try:
                action = self._llm.get_next_action(
                    screenshot=screenshot,
                    goal=task.goal,
                    history=state.get_history_for_llm(),
                )
            except Exception as e:
                state.mark_failed(f"LLM error: {e}")
                return TaskResult(
                    success=False,
                    steps_taken=step,
                    error=str(e),
                    run_id=task.run_id,
                )

            # Check for terminal actions
            if isinstance(action, DoneAction):
                record = StepRecord(
                    step=step,
                    action_type="DONE",
                    action_data=action.model_dump(),
                    result_ok=True,
                    screenshot_path=str(screenshot_path),
                )
                state.add_step(record)
                state.mark_completed(action.final_answer)
                return TaskResult(
                    success=True,
                    steps_taken=step,
                    final_answer=action.final_answer,
                    run_id=task.run_id,
                )

            if isinstance(action, FailAction):
                record = StepRecord(
                    step=step,
                    action_type="FAIL",
                    action_data=action.model_dump(),
                    result_ok=False,
                    screenshot_path=str(screenshot_path),
                    error=action.error,
                )
                state.add_step(record)
                state.mark_failed(action.error)
                return TaskResult(
                    success=False,
                    steps_taken=step,
                    error=action.error,
                    run_id=task.run_id,
                )

            # --- ACT ---
            exec_result = self._executor.execute(action)

            # Record step
            record = StepRecord(
                step=step,
                action_type=action.type,
                action_data=action.model_dump(),
                result_ok=exec_result.ok,
                screenshot_path=str(screenshot_path),
                error=exec_result.error,
            )
            state.add_step(record)

            if not exec_result.ok:
                # Execution failed, but continue - let LLM decide what to do
                pass

        # Max steps reached
        state.mark_failed("Max steps reached without completing task")
        return TaskResult(
            success=False,
            steps_taken=task.max_steps,
            error="Max steps reached without completing task",
            run_id=task.run_id,
        )

    def _save_metadata(
        self,
        run_dir: Path,
        task: Task,
        state: AgentState,
        result: TaskResult,
    ) -> None:
        """Save run metadata to JSON file."""
        metadata = {
            "task": {
                "goal": task.goal,
                "max_steps": task.max_steps,
                "run_id": task.run_id,
            },
            "result": result.to_dict(),
            "llm": {
                "provider": self._llm.info().provider,
                "model": self._llm.info().model,
            },
            "state": state.to_dict(),
            "timestamp": datetime.now().isoformat(),
        }

        metadata_path = run_dir / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
