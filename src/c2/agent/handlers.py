import platform
import time
from typing import Any


def get_host_metadata(parameters: dict[str, Any]) -> dict[str, str]:
    if parameters:
        raise ValueError("get_host_metadata does not accept parameters")

    return {
        "hostname": platform.node(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
    }


def echo(parameters: dict[str, Any]) -> dict[str, str]:
    text = parameters.get("text")

    if not isinstance(text, str):
        raise ValueError("echo requires text")

    if len(text) > 1_000:
        raise ValueError("echo text is too long")

    return {"text": text}


def sleep_task(parameters: dict[str, Any]) -> dict[str, str]:
    seconds = parameters.get("seconds")

    if not isinstance(seconds, int) or not 0 <= seconds <= 30:
        raise ValueError("sleep must be an integer between 0 and 30")

    time.sleep(seconds)

    return {"slept_seconds": seconds}

TASK_HANDLERS = {
    "get_host_metadata": get_host_metadata,
    "echo": echo,
    "sleep": sleep_task,
}


def execute_task(
    task_type: str,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    handler = TASK_HANDLERS.get(task_type)

    if handler is None:
        raise ValueError(f"Unsupported task type: {task_type}")

    return handler(parameters)