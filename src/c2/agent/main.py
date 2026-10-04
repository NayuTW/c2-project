import argparse
import platform
import time

import httpx

from c2.agent.client import C2Client
from c2.agent.handlers import execute_task


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Educational C2 afent simulator"
    )
    
    parser.add_argument(
        "--server",
        default="http://127.0.0.1:8000",
        help="Base URL of the C2 server",
    )

    parser.add_argument(
        "--enrollment-token",
        default="development-only-token",
        help="Development enrollment token",
    )

    parser.add_argument(
        "--version",
        default="0.1.0",
        help="Agent version",
    )

    parser.add_argument(
        "--poll-once",
        action="store_true",
        help="Register, poll once, process tasks, and exit",
    )

    return parser.parse_args()


def register_agent(
    client: C2Client,
    enrollment_token: str,
    agent_version: str,
) -> tuple[str, str, int]:
    response = client.register(
        enrollment_token=enrollment_token,
        agent_version=agent_version,
        platform=platform.system().lower(),
        architecture=platform.machine(),
    )

    agent_id = response["agent_id"]
    session_token = response["session_token"]
    poll_interval = response["poll_interval_seconds"]

    print(f"Registered as {agent_id}")
    print(f"Polling every {poll_interval} seconds")

    return agent_id, session_token, poll_interval


def process_task(
    client: C2Client,
    agent_id: str,
    session_token: str,
    task: dict,
) -> None:
    task_id = task.get("task_id")
    task_type = task.get("task_type")
    parameters = task.get("parameters", {})

    if not isinstance(task_id, str):
        print("Rejecting task with invalid task_id")
        return

    if not isinstance(task_type, str):
        print(f"Rejecting task {task_id}: invalid task_type")
        return

    if not isinstance(parameters, dict):
        print(f"Rejecting task {task_id}: parameters must be an object")
        return

    print(f"Received task {task_id}: {task_type}")
    
    try:
        result = execute_task(task_type, parameters)

    except Exception as exc:
        error_message = str(exc)
        
        print(f"Task {task_id} failed: {error_message}")

        client.submit_result(
            agent_id=agent_id,
            session_token=session_token,
            task_id=task_id,
            status="failed",
            error=error_message,
        )

    else:
        print(f"Task {task_id} completed: {result}")

        client.submit_result(
            agent_id=agent_id,
            session_token=session_token,
            task_id=task_id,
            status="completed",
            result=result,
        )


def run_agent(args: argparse.Namespace) -> None:
    client = C2Client(args.server)

    agent_id, session_token, poll_interval = register_agent(
        client=client,
        enrollment_token=args.enrollment_token,
        agent_version=args.version,
    )

    while True:
        try:
            response = client.poll(
                agent_id=agent_id,
                session_token=session_token,
            )

            tasks = response.get("tasks", [])

            if not isinstance(tasks, list):
                print("Server returned an invalid tasks value")
                tasks = []

            if not tasks:
                print("No tasks")

            for task in tasks:
                if isinstance(task, dict):
                    process_task(
                        client=client,
                        agent_id=agent_id,
                        session_token=session_token,
                        task=task,
                    )
                else:
                    print("Ignoring malformed task")

            if args.poll_once:
                break

            time.sleep(poll_interval)
        
        except httpx.HTTPStatusError as exc:
            print(
                f"HTTP error: "
                f"{exc.response.status_code} "
                f"{exc.response.text}"
            )

            if args.poll_once:
                break

            time.sleep(poll_interval)

        except httpx.RequestError as exc:
            print(f"Network error: {exc}")

            if args.poll_once:
                break

            time.sleep(poll_interval)


def main() -> None:
    args = parse_args()

    try:
        run_agent(args)
    except KeyboardInterrupt:
        print("\nAgent stopped")


if __name__ == "__main__":
    main()