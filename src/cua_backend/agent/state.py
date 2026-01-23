"""
Agent state tracking for the Computer Use Agent.
Tracks step count, action history, and execution status.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentStatus(Enum):
    """Current status of the agent."""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class StepRecord:
    """Record of a single step in the agent execution."""

    step: int
    action_type: str
    action_data: Dict[str, Any]
    result_ok: bool
    screenshot_path: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "action_type": self.action_type,
            "action": self.action_data,
            "result_ok": self.result_ok,
            "screenshot_path": self.screenshot_path,
            "error": self.error,
        }


@dataclass
class AgentState:
    """
    Tracks the current state of the agent during task execution.
    Maintains history for context and logging.
    """

    goal: str
    max_steps: int
    step_count: int = 0
    status: AgentStatus = AgentStatus.IDLE
    history: List[StepRecord] = field(default_factory=list)
    final_answer: Optional[str] = None
    error: Optional[str] = None

    def add_step(self, record: StepRecord) -> None:
        """Add a step record to history."""
        self.history.append(record)
        self.step_count = record.step

    def get_history_for_llm(self) -> List[Dict[str, Any]]:
        """Get history formatted for LLM context (last 5 steps)."""
        return [step.to_dict() for step in self.history[-5:]]

    def is_terminal(self) -> bool:
        """Check if agent has reached a terminal state."""
        return self.status in (AgentStatus.COMPLETED, AgentStatus.FAILED)

    def mark_running(self) -> None:
        self.status = AgentStatus.RUNNING

    def mark_completed(self, final_answer: Optional[str] = None) -> None:
        self.status = AgentStatus.COMPLETED
        self.final_answer = final_answer

    def mark_failed(self, error: str) -> None:
        self.status = AgentStatus.FAILED
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "max_steps": self.max_steps,
            "step_count": self.step_count,
            "status": self.status.value,
            "final_answer": self.final_answer,
            "error": self.error,
            "history": [step.to_dict() for step in self.history],
        }
