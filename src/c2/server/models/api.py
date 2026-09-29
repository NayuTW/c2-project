from typing import Any, Literal
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    enrollment_token: str = Field(min_length=1, max_length=200)
    agent_version: str = Field(min_length=1, max_length=50)
    platform: str = Field(min_length=1, max_length=50)
    architecture: str = Field(min_length=1, max_length=50)


class RegisterResponse(BaseModel):
    agent_id: str
    session_token: str
    poll_interval_seconds: int


class PollRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=100)
    session_token: str = Field(min_length=1, max_length=500)


class CreateTaskRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=100)
    task_type: Literal[
        "get_host_metadata",
        "echo",
        "sleep",
    ]
    parameters: dict[str, Any] = Field(default_factory=dict)


class PollResponse(BaseModel):
    tasks: list[Task]


class TaskResultRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=100)
    session_token: str = Field(min_length=1, max_length=500)
    task_id: str = Field(min_length=1, max_length=100)
    status: Literal["completed", "failed"]
    result: dict[str, Any] | None = None
    error: str | None = Field(default=None, max_length=1_000)


class TaskResultResponse(BaseModel):
    accepted: bool
