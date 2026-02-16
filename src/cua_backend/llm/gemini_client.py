"""
Gemini LLM client implementing the LLMClient interface.
Takes screenshot + goal + history, returns validated Action JSON.
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
from typing import Any, Dict, List, Optional

from PIL import Image

try:
    import google.genai as genai
except ImportError:
    genai = None

from ..schemas.actions import (
    Action,
    ClickAction,
    TypeAction,
    ScrollAction,
    PressKeyAction,
    WaitAction,
    DoneAction,
    FailAction,
)
from .base import LLMClient, LLMInfo
from .prompt_templates import SYSTEM_PROMPT, build_user_message


class GeminiClient(LLMClient):
    """
    Gemini API wrapper that implements the LLMClient interface.
    Uses Gemini 2.0 Flash for vision + text understanding.
    """

    DEFAULT_MODEL = "gemini-2.5-flash"
    MAX_RETRIES = 3

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        if genai is None:
            raise ImportError(
                "google-generativeai is not installed. "
                "Run: uv add google-generativeai"
            )

        self._api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self._api_key:
            raise ValueError(
                "GEMINI_API_KEY not found. Set it as an environment variable "
                "or pass api_key to the constructor."
            )

        self._model_name = model or self.DEFAULT_MODEL
        genai.configure(api_key=self._api_key)
        self._model = genai.GenerativeModel(
            model_name=self._model_name,
            system_instruction=SYSTEM_PROMPT,
        )

    def info(self) -> LLMInfo:
        return LLMInfo(provider="google", model=self._model_name)

    def get_next_action(
        self,
        screenshot: Image.Image,
        goal: str,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Action:
        """
        Send screenshot + goal to Gemini, parse and validate the action JSON.
        Retries up to MAX_RETRIES times if JSON parsing or validation fails.
        """
        user_message = build_user_message(goal, history)
        image_part = self._encode_image(screenshot)

        last_error: Optional[Exception] = None

        for attempt in range(self.MAX_RETRIES):
            try:
                response = self._model.generate_content([image_part, user_message])
                raw_text = response.text.strip()
                action = self._parse_action(raw_text)
                return action

            except (json.JSONDecodeError, ValueError) as e:
                last_error = e
                # Add hint for retry
                user_message = (
                    f"Your previous response was invalid: {e}\n"
                    f"Please respond with ONLY valid JSON.\n\n"
                    f"{build_user_message(goal, history)}"
                )
                continue

        # All retries exhausted
        raise ValueError(
            f"Failed to get valid action after {self.MAX_RETRIES} attempts. "
            f"Last error: {last_error}"
        )

    def _encode_image(self, image: Image.Image) -> dict:
        """Convert PIL Image to base64 for Gemini API."""
        buffer = io.BytesIO()
        # Convert to RGB if necessary (handles RGBA, etc.)
        if image.mode != "RGB":
            image = image.convert("RGB")
        image.save(buffer, format="JPEG", quality=85)
        image_bytes = buffer.getvalue()

        return {
            "mime_type": "image/jpeg",
            "data": base64.b64encode(image_bytes).decode("utf-8"),
        }

    def _parse_action(self, raw_text: str) -> Action:
        """
        Parse raw LLM output into a validated Action.
        Handles JSON wrapped in markdown code blocks.
        """
        # Strip markdown code block if present
        text = raw_text.strip()
        if text.startswith("```"):
            # Remove ```json or ``` prefix and trailing ```
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        data = json.loads(text)

        if not isinstance(data, dict):
            raise ValueError(f"Expected JSON object, got {type(data).__name__}")

        action_type = data.get("type")
        if not action_type:
            raise ValueError("Missing 'type' field in action JSON")

        # Map type string to Pydantic model
        type_map = {
            "CLICK": ClickAction,
            "TYPE": TypeAction,
            "SCROLL": ScrollAction,
            "PRESS_KEY": PressKeyAction,
            "WAIT": WaitAction,
            "DONE": DoneAction,
            "FAIL": FailAction,
        }

        model_class = type_map.get(action_type)
        if not model_class:
            raise ValueError(
                f"Unknown action type: {action_type}. "
                f"Valid types: {list(type_map.keys())}"
            )

        # Validate using Pydantic
        return model_class.model_validate(data)
