from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from PIL import Image

from ..schemas.actions import Action


@dataclass
class LLMInfo:
    provider: str
    model: str


class LLMClient(ABC):
    """
    Every LLM provider must implement this exact interface.
    The agent should not care which LLM is behind it.
    """

    @abstractmethod
    def info(self) -> LLMInfo:
        raise NotImplementedError

    @abstractmethod
    def get_next_action(
        self,
        screenshot: Image.Image,
        goal: str,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Action:
        """
        Input: screenshot + goal + small history
        Output: ONE Action (from schemas/actions.py)
        """
        raise NotImplementedError
