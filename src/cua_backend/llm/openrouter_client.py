"""
openrouter_client.py - Professional OpenRouter Integration
=========================================================
Implements the LLMClient interface using LiteLLM for OpenRouter.
Supports both text-only planning and vision fallback.
"""

from __future__ import annotations

import os
import base64
from io import BytesIO
from typing import Any, Dict, List, Optional
from PIL import Image

import litellm
from .base import LLMClient, LLMInfo
from ..schemas.actions import Action

class OpenRouterClient(LLMClient):
    """
    LiteLLM-based adapter for OpenRouter.
    Uses OPENROUTER_API_KEY from environment.
    """
    
    def __init__(self, model: str = "openrouter/google/gemini-2.0-flash-lite:free"):
        """
        Initialize the client.
        
        Args:
            model: OpenRouter model string (e.g., 'openrouter/anthropic/claude-3-haiku')
        """
        self._model = model
        self._api_key = os.getenv("OPENROUTER_API_KEY")
        
        # OpenRouter specific headers for "Rankings" and "App Name"
        self._extra_headers = {
            "HTTP-Referer": "https://github.com/3xCaffeine/DeskPilot",
            "X-Title": "DeskPilot CUA",
        }

    def info(self) -> LLMInfo:
        return LLMInfo(provider="openrouter", model=self._model)

    def get_next_action(
        self,
        screenshot: Image.Image,
        goal: str,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Action:
        """
        Vision request via OpenRouter.
        (Note: Most free models don't support vision, but many paid ones do.)
        """
        # Convert PIL to Base64
        buffered = BytesIO()
        screenshot.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Goal: {goal}\nRespond with a single action JSON."},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_str}"}
                    },
                ],
            }
        ]

        # Use litellm for the call
        response = litellm.completion(
            model=self._model,
            messages=messages,
            api_key=self._api_key,
            headers=self._extra_headers,
            response_format={"type": "json_object"}
        )
        
        # Parse result
        try:
            import json
            content = response.choices[0].message.content
            data = json.loads(content)
            
            # Simple mapping from JSON to Action objects
            from ..schemas.actions import ClickAction, TypeAction, PressKeyAction, WaitAction, DoneAction, FailAction
            
            a_type = data.get("type", "").upper()
            if a_type == "CLICK":
                return ClickAction(x=data.get("x", 0), y=data.get("y", 0), reason=data.get("reason", ""))
            elif a_type == "TYPE":
                return TypeAction(text=data.get("text", ""), reason=data.get("reason", ""))
            elif a_type == "PRESS_KEY":
                return PressKeyAction(key=data.get("key", ""), reason=data.get("reason", ""))
            elif a_type == "DONE":
                return DoneAction(final_answer=data.get("final_answer", ""), reason=data.get("reason", ""))
            
            return FailAction(error=f"Unsupported action type from vision: {a_type}", reason=content)
            
        except Exception as e:
            from ..schemas.actions import FailAction
            return FailAction(error=f"Failed to parse OpenRouter response: {e}", reason=response.choices[0].message.content)
