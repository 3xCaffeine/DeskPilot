"""
Task definition models for the Computer Use Agent.
Defines the structure of tasks to execute and their results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4


@dataclass
class Task:
    """A task for the agent to complete."""

    goal: str
    max_steps: int = 50
    run_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))

    def __post_init__(self):
        if not self.goal.strip():
            raise ValueError("Task goal cannot be empty")
        if self.max_steps < 1:
            raise ValueError("max_steps must be at least 1")


@dataclass
class TaskResult:
    """Result of a completed task execution."""

    success: bool
    steps_taken: int
    final_answer: Optional[str] = None
    error: Optional[str] = None
    run_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "steps_taken": self.steps_taken,
            "final_answer": self.final_answer,
            "error": self.error,
            "run_id": self.run_id,
        }
