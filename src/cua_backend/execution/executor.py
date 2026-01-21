from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from PIL import Image

from ..schemas.actions import Action


@dataclass
class ExecutionResult:
    ok: bool
    error: Optional[str] = None


class Executor(ABC):
    """
    Any desktop controller must implement this.
    This is how the agent 'uses the computer'.
    """

    @abstractmethod
    def screenshot(self) -> Image.Image:
        """Take a screenshot of the current desktop."""
        raise NotImplementedError

    @abstractmethod
    def execute(self, action: Action) -> ExecutionResult:
        """Perform one action: click/type/scroll/etc."""
        raise NotImplementedError
