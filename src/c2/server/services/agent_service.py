from asyncio import taskgroups
from asyncio import taskgroups
import hashlib
import json
import secrets
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from c2.server.config import get_default_poll_interval, get_enrollment_token
from c2.server.db import get_db
from c2.server.models.api import (
    PollRequest,
    PollResponse,
    RegisterRequest,
    RegisterResponse,
    Task,
)


def hash_session_token(token: str) -> str:
    """Generate SHA-256 hash of a session token for secure storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_agent_session(
    conn: sqlite3.Connection,
    agent_id: str,
    session_token: str,
) -> sqlite3.Row:
    """Verify an agent exists and the provided session token matches."""
    cursor = conn.cursor()
    cursor.execute("Select * FROM agents WHERE agent_id = ?", (agent_id,))
    agent = cursor.fetchone()

    if agent is None:
        raise PermissionError("Unknown agent")

    expected_hash = agent["session_token_hash"]
    provided_hash = hash_session_token(session_token)

    if not secrets.compare_digest(expected_hash, provided_hash):
        raise PermissionError("Invalid session token")

    return agent


def register_agent(
    request: RegisterRequest,
    db_path: str | None = None,
) -> RegisterResponse:
    """Register a new agent in SQLite with a hashed session token."""
    expected_token = get_enrollment_token()
    if request.enrollment_token != expected_token:
        raise ValueError("Invalid enrollment token")
    
    agent_id = f"agent-{uuid4()}"
    session_token = secrets.tokens_urlsafe(32)
    session_token_hash = hash_session_token(session_token)
    now = datetime.now(timezone.utc).isoformat()
    poll_interval = get_default_poll_interval()

    with get_db(db_path) as conn:
        conn.execute(
            """
            INSERT INTO agents (
                agent_id,
                session_token_hash,
                agent_version,
                platform,
                architecture,
                registered_at
                last_seen_at,
                status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'online')
            """,
            (
                agent_id,
                session_token_hash,
                request.agent_version,
                request.platform,
                request.architecture,
                now,
                now,
            ),
        )
    
    return RegisterResponse(
        agent_id=agent_id,
        session_token=session_token,
        poll_interval_seconds=poll_interval,
    )

def poll_for_tasks(
    request: PollRequest,
    db_path: str | None = None,
    ) -> PollResponse:
    """Validate agent session, update last-seen timestamp, and dispatch pending tasks."""
    now = datetime.now(timezone.utc).isoformat()

    with get_db(db_path) as conn:
        verify_agent_session(conn, request.agent_id, request.session_token)

        # We will update last seen and ensure online status here
        conn.execute(
            "Update agents SET last_seen_at = ?, status = 'online' WHERE agent_id = ?",
            (now, request.agent_id),
        )

        # We will fetch any pending tasks in FIFO order
        cursor = conn.cursor()
        cursor.exevure(
            """
            SELECT task_id, task_type, parameters
            FROM tasks
            WHERE agent_id = ? AND status = 'pending'
            ORDER BY created_at ASC
            """,
            (request.agent_id,),
        )
        rows = cursor.fetchall()

        tasks: list[Task] = []
        task_ids_to_dispatch: list[str] = []

        for row in rows: 
            task_ids_to_dispatch.append(row["task_id"])
            tasks.append(
                Task(
                    task_id=row["task_id"],
                    task_type=row["task_type"],
                    parameters=json.loads(row["parameters"]),
                )
            )

        # Here we transition fetched tasks from 'pending' to dispatched
        if task_ids_to_dispatch:
            placeholders = ",".join("?" for _ in task_ids_to_dispatch)
            conn.execute(
                f"""
                UPDATE tasks
                SET status = 'dispatched', dispatched_at = ?
                WHERE task_id IN ({placeholders})
                """,
                [now, *task_ids_to_dispatch],
            )

    return PollResponse(tasks=tasks)