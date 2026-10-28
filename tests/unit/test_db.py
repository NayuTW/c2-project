import sqlite3
import pytest

from c2.server.db import get_connection, get_db, init_db
from c2.server.models.api import (
    CreateTaskRequest,
    PollRequest,
    RegisterRequest,
    TaskResultRequest,
)
from c2.server.services.agent_service import poll_for_tasks, register_agent
from c2.server.services.task_service import create_task, submit_result


@pytest.fixture
def test_db_path(tmp_path):
    """Provides a fresh isolated SQLite file database for each test."""
    db_file = str(tmp_path / "test_c2.db")
    init_db(db_file)
    return db_file


def test_init_db_creates_tables(test_db_path):
    conn = get_connection(test_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row["name"] for row in cursor.fetchall()}
    conn.close()

    expected_tables = {"agents", "tasks", "task_results", "audit_logs"}
    assert expected_tables.issubset(tables)


def test_agent_registration_and_polling(test_db_path):
    reg_req = RegisterRequest(
        enrollment_token="development-only-token",
        agent_version="0.1.0",
        platform="linux",
        architecture="x86_64",
    )
    reg_resp = register_agent(reg_req, db_path=test_db_path)
    assert reg_resp.agent_id.startswith("agent-")
    assert reg_resp.session_token

    with get_db(test_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT session_token_hash FROM agents WHERE agent_id = ?", (reg_resp.agent_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["session_token_hash"] != reg_resp.session_token

    with pytest.raises(PermissionError, match="Invalid session token"):
        poll_for_tasks(
            PollRequest(agent_id=reg_resp.agent_id, session_token="wrong_token"),
            db_path=test_db_path,
        )

    poll_resp = poll_for_tasks(
        PollRequest(agent_id=reg_resp.agent_id, session_token=reg_resp.session_token),
        db_path=test_db_path,
    )
    assert poll_resp.tasks == []

def test_task_lifecycle_in_db(test_db_path):
    reg_resp = register_agent(
        RegisterRequest(
            enrollment_token="development-only-token",
            agent_version="0.1.0",
            platform="linux",
            architecture="x86_64",
        ),
        db_path=test_db_path,
    )
    created_task = create_task(
        CreateTaskRequest(
            agent_id=reg_resp.agent_id,
            task_type="echo",
            parameters={"text": "hello sqlite"},
        ),
        db_path=test_db_path,
    )
    poll_resp = poll_for_tasks(
        PollRequest(agent_id=reg_resp.agent_id, session_token=reg_resp.session_token),
        db_path=test_db_path,
    )
    assert len(poll_resp.tasks) == 1
    assert poll_resp.tasks[0].task_id == created_task.task_id
    with get_db(test_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, dispatched_at FROM tasks WHERE task_id = ?", (created_task.task_id,))
        task_row = cursor.fetchone()
        assert task_row["status"] == "dispatched"
        assert task_row["dispatched_at"] is not None
    submit_result(
        created_task.task_id,
        TaskResultRequest(
            agent_id=reg_resp.agent_id,
            session_token=reg_resp.session_token,
            task_id=created_task.task_id,
            status="completed",
            result={"text": "hello sqlite"},
        ),
        db_path=test_db_path,
    )
    with get_db(test_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, completed_at FROM tasks WHERE task_id = ?", (created_task.task_id,))
        assert cursor.fetchone()["status"] == "completed"
        cursor.execute("SELECT status, result FROM task_results WHERE task_id = ?", (created_task.task_id,))
        result_row = cursor.fetchone()
        assert result_row["status"] == "completed"
        assert "hello sqlite" in result_row["result"]
