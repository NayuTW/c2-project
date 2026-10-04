from platform import architecture
from anyio._core import _tasks
from secrets import token_urlsafe
from uuid import uuid4

from c2.server.models.api import (
    PollRequest,
    PollResponse,
    RegisterRequest,
    RegisterResponse,
    Task,
)

EXPECTED_ENROLLMENT_TOKEN = "development-only-token"

_agents: dict[str, dict] = {}
_tasks: dict[str, list[Task]] = {}


def register_agent(request: RegisterRequest) -> RegisterResponse:
    if request.enrollment_token != EXPECTED_ENROLLMENT_TOKEN:
        raise ValueError("Invalid enrollment token")
    
    agent_id = f"agent-{uuid4()}"
    session_token = token_urlsafe(32)

    _agents[agent_id] = {
        "agent_id": agent_id,
        "session_token": session_token,
        "agent_version": request.agent_version,
        "platform": request.platform,
        "architecture": request.architecture,
    }

    _tasks[agent_id] = []

    return RegisterResponse(
        agent_id=agent_id,
        session_token=session_token,
        poll_interval_seconds=10,
    )

def poll_for_tasks(request: PollRequest) -> PollResponse:
    agent = _agents.get(request.agent_id)

    if agent is None:
        raise PermissionError("Unknown agent")
        
    if agent["session_token"] != request.session_token:
        raise PermissionError("Invalid session token")

    tasks = _tasks.get(request.agent_id, [])

    # For simple first version, deliver all queued tasks.
    _tasks[request.agent_id] = []

    return PollResponse(tasks=tasks)


def add_task_for_agent(agent_id: str, task: Task) -> None:
    if agent_id not in _agents:
        raise ValueError("Unknown agent")

    _tasks.setdefault(agent_id, []).append(task)