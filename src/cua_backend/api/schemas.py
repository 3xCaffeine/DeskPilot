"""API request/response models."""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal


class TaskCreateRequest(BaseModel):
    goal: str = Field(..., min_length=1)
    model: str = Field(default="openrouter/google/gemini-2.0-flash-001")
    max_steps: int = Field(default=10, ge=1, le=100)


class TaskCreateResponse(BaseModel):
    task_id: str
    goal: str
    status: str = "queued"


class StepEvent(BaseModel):
    event_type: Literal["step", "completed", "failed", "cancelled"] = "step"
    step: int = 0
    action_type: str = ""
    action_detail: str = ""
    result_ok: bool = True
    error: Optional[str] = None
    screenshot_available: bool = False
    timestamp: str = ""


class TaskSummary(BaseModel):
    task_id: str
    goal: str
    status: str
    model: str = ""
    steps_taken: int = 0
    final_answer: Optional[str] = None
    error: Optional[str] = None
    created_at: str = ""


class RandomTaskResponse(BaseModel):
    task: str


class ConfigResponse(BaseModel):
    default_model: str
    default_max_steps: int
    available_models: List[str]
    docker_status: str = "unknown"
    vnc_url: str = "http://localhost:6080/vnc.html"
    openrouter_key_set: bool = False
    gemini_key_set: bool = False


class ConfigUpdateRequest(BaseModel):
    default_model: Optional[str] = None
    default_max_steps: Optional[int] = None
    openrouter_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
