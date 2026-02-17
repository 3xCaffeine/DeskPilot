from __future__ import annotations

from typing import Literal, Optional, Union
from pydantic import BaseModel, Field


# Base action (all actions have these)
class ActionBase(BaseModel):
    type: str
    reason: str = Field(default="", description="Why the agent is doing this")


# ---- Basic actions ----

class ClickAction(ActionBase):
    type: Literal["CLICK"] = "CLICK"
    x: int = Field(ge=0)
    y: int = Field(ge=0)


class TypeAction(ActionBase):
    type: Literal["TYPE"] = "TYPE"
    text: str = Field(min_length=1)


class ScrollAction(ActionBase):
    type: Literal["SCROLL"] = "SCROLL"
    amount: int = Field(description="Positive = scroll down, Negative = scroll up")


class PressKeyAction(ActionBase):
    type: Literal["PRESS_KEY"] = "PRESS_KEY"
    key: str = Field(description="Keyboard key name like ENTER, TAB, CTRL+L")


class WaitAction(ActionBase):
    type: Literal["WAIT"] = "WAIT"
    seconds: float = Field(ge=0.1, le=10.0)


# ---- Terminal actions ----

class DoneAction(ActionBase):
    type: Literal["DONE"] = "DONE"
    final_answer: Optional[str] = None


class FailAction(ActionBase):
    type: Literal["FAIL"] = "FAIL"
    error: str


# ---- Browser actions (CDP-based) ----

class BrowserNavigateAction(ActionBase):
    type: Literal["BROWSER_NAVIGATE"] = "BROWSER_NAVIGATE"
    url: str = Field(description="URL to navigate to")


class BrowserClickAction(ActionBase):
    type: Literal["BROWSER_CLICK"] = "BROWSER_CLICK"
    element_index: int = Field(description="Index of element from interactive elements list")


class BrowserTypeAction(ActionBase):
    type: Literal["BROWSER_TYPE"] = "BROWSER_TYPE"
    element_index: int = Field(description="Index of input element from interactive elements list")
    text: str = Field(min_length=1)



# Union type (the LLM must return ONE of these)
Action = Union[
    ClickAction,
    TypeAction,
    ScrollAction,
    PressKeyAction,
    WaitAction,
    DoneAction,
    FailAction,
    BrowserNavigateAction,
    BrowserClickAction,
    BrowserTypeAction,
]
