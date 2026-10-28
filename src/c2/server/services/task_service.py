import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from c2.server.db import get_db
from c2.server.models.api import (
    CreateTaskRequest,
    Task,
    TaskResultRequest,
)
from c2.server.services.agent_service import verify_agent_session

SUPPORTED_TASKS = {
    "get_host_metadata",
    "echo",
    "sleep",
}


def create_task(
    request: CreateTaskRequest,
    db_path: str | None = None,
) -> Task:
    if request.task_type not in SUPPORTED_TASKS:
        raise ValueError("Unsupported task type")
    
    validate_task_parameters(
        request.task_type,
        request.parameters,
    )

    task_id = f"task-{uuid4()}"
    now = datetime.now(timezone.utc).isoformat()

    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT agent_id FROM agents WHERE agent_id = ?", (request.agent_id,))
        if cursor.fetchone() is None:
            raise ValueError("Unknown agent")

        conn.execute(
            """
            INSERT INTO tasks (
                task_id,
                agent_id,
                task_type,
                parameters,
                status,
                created_at
            ) VALUES (?, ?, ?, ?, 'pending', ?)
            """,
            (
                task_id,
                request.agent_id,
                request.task_type,
                json.dumps(request.parameters),
                now,
            ),
        )
    return Task(
        task_id=task_id,
        task_type=request.task_type,
        parameters=request.parameters,
    )


def submit_result(
    task_id: str,
    request: TaskResultRequest,
    db_path: str | None = None,
) -> None:
    if task_id != request.task_id:
        raise ValueError("Task ID mismatch")
        
    if request.status == "failed" and not request.error:
        raise ValueError("Failed tasks must include an error")

    now = datetime.now(timezone.utc).isoformat()

    with get_db(db_path) as conn:
        # Here we verify the submitting agent's authentication
        verify_agent_session(conn, request.agent_id, request.session_token)

        cursor = conn.cursor()
        cursor.execute(
            "SELECT agent_id, status FROM tasks WHERE task_id = ?",
            (task_id,),
        )
        task = cursor.fetchone()

        if task is None:
            raise ValueError("Unknown task")

        if task["agent_id"] != request.agent_id:
            raise ValueError("Task does not belong to this agent")

        # This is where we save result record
        conn.execute(
            """
            INSERT INTO task_results(
                task_id,
                status,
                result,
                error,
                received_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                task_id,
                request.status,
                json.dumps(request.result) if request.result is not None else None,
                request.error,
                now,
            ),
        )

        # Here we will update task status and completion time
        conn.execute(
            "UPDATE tasks SET status = ?, completed_at = ? WHERE task_id = ?",
            (request.status, now, task_id),
        )


# We will validate task structure here
# but we will also validate it agent client side
def validate_task_parameters(
    task_type: str,
    parameters: dict[str, Any],
) -> None:
    if task_type == "get_host_metadata":
        if parameters:
            raise ValueError("get_host_metadata does not accept parameters")
    elif task_type == "echo":
        text = parameters.get("text")

        if not isinstance(text, str):
            raise ValueError("echo requires a text string")
        
        if len(text) > 1_000:
            raise ValueError("echo text is too long")
    elif task_type == "sleep":
        seconds = parameters.get("seconds")

        if not isinstance(seconds, int):
            raise ValueError("sleep requires an integer duration")

        if not 0 <= seconds <= 30:
            raise ValueError("sleep duration must be between 0 and 30 seconds")
