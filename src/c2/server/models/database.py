from dataclasses import dataclass
from typing import Any


@dataclass
class AgentRecord:
    agent_id: str
    session_token_hash: str
    agent_version: str
    platform: str
    architecture: str
    registered_at: str
    last_seen_at: str
    status: str = "online"


@dataclass
class TaskRecord:
    task_id: str
    agent_id: str
    task_type: str
    parameters: dict[str, Any]
    status: str
    created_at: str
    dispatched_at: str | None = None
    completed_at: str | None = None


@dataclass
class TaskResultRecord:
    task_id: str
    status: str
    result: dict[str, Any] | None
    error: str | None
    received_at: str


@dataclass
class AuditLogRecord:
    id: int | None
    timestamp: str
    event_type: str
    agent_id: str | None
    details: dict[str, Any]
    ip_address: str | None = None