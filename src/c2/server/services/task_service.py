from typing import Any
from uuid import uuid4

from c2.server.models.api import (
    CreateTaskRequest,
    Task,
    TaskResultRequest,
)
from c2.server import agent_service

SUPPORTED_TASKS = {
    "get_host_metadata",
    "echo",
    "sleep",
}


def create_task(request: CreateTaskRequest) -> Task:
    if request.task_type not in SUPPORTED_TASKS:
        raise ValueError("Unsupported task type")
    
    validate_task_parameters(
        request.task_type,
        request.parameters,
    )

    task = Task(
        task_id=f"task-{uuid4()}",
        task_type=request.task_type,
        parameters=request.parameters,
    )

    agent_service.add_task_for_agent(request.agent_id, task)
    
    return task

def submit_result(
    task_id: str,
    request: TaskResultRequest,
) -> None:
    if task_id != request.task_id:
        raise ValueError("Task ID mismatch")
        
    if request.status == "failed" and not request.error:
        raise ValueError("Failed tasks must not include an error")

    # For Milestone 1, we just print the result.
    # Later it will be stored in SQLite.
    print(
        f"Result received for {task_id}"
        f"status={request.status}, result={request.result}"
    )


def validate_task_parameters(
    task_type: str,
    parameters: dict[str, Any],
) -> None:
    if task_type == "get_host_metadata":
        if parameters:
            raise ValueError(
                "get_host_metadata does not accept parameters"
            )
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