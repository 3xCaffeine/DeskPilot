from pydantic import BaseModel, Field

class Task(BaseModel):
    name: str = Field(..., description="Name of the task")
    description: str = Field(..., description="Description of what the agent needs to do")
    max_steps: int = Field(default=10, description="Maximum number of steps allowed for this task")
