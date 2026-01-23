"""Schemas module for the Computer Use Agent."""

from .actions import (
    Action,
    ActionBase,
    ClickAction,
    TypeAction,
    ScrollAction,
    PressKeyAction,
    WaitAction,
    DoneAction,
    FailAction,
)
from .tasks import Task, TaskResult

__all__ = [
    "Action",
    "ActionBase",
    "ClickAction",
    "TypeAction",
    "ScrollAction",
    "PressKeyAction",
    "WaitAction",
    "DoneAction",
    "FailAction",
    "Task",
    "TaskResult",
]
