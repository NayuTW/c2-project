import io
import json
from contextlib import redirect_stdout
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from c2.cli import main as cli_main
from c2.server.app import app
from c2.server.db import get_db, init_db
from c2.server.models.api import (
    CreateTaskRequest,
    PollRequest,
    RegisterRequest,
    TaskResultRequest,
)
from c2.server.services.agent_service import (
    check_agent_timeouts,
    poll_for_tasks,
    register_agent,
)
from c2.server.services.task_service import create_task, submit_result


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Configure an isolated SQLite database via C2_DB_PATH for API tests."""
    db_file = str(tmp_path / "test_operator.db")
    monkeypatch.setenv("C2_DB_PATH", db_file)
    monkeypatch.setenv("C2_OPERATOR_KEY", "test-op-key")
    init_db(db_file)
    return db_file


def _register_and_complete_task(db_file: str) -> tuple[str, str, str]:
    reg = register_agent(
        RegisterRequest(
            enrollment_token="development-only-token",
            agent_version="0.1.0",
            platform="linux",
            architecture="x86_64",
        ),
        db_path=db_file,
    )
    task = create_task(
        CreateTaskRequest(
            agent_id=reg.agent_id,
            task_type="echo",
            parameters={"text": "hello operator"},
        ),
        db_path=db_file,
    )
    poll_for_tasks(
        PollRequest(agent_id=reg.agent_id, session_token=reg.session_token),
        db_path=db_file,
    )
    submit_result(
        task.task_id,
        TaskResultRequest(
            agent_id=reg.agent_id,
            session_token=reg.session_token,
            task_id=task.task_id,
            status="completed",
            result={"text": "hello operator"},
        ),
        db_path=db_file,
    )
    return reg.agent_id, reg.session_token, task.task_id


def test_operator_auth_required(isolated_db):
    with TestClient(app) as client:
        missing = client.get("/api/v1/operator/agents")
        assert missing.status_code == 422

        wrong = client.get(
            "/api/v1/operator/agents",
            headers={"x-operator-key": "wrong-key"},
        )
        assert wrong.status_code == 401
        assert wrong.json()["detail"] == "Invalid operator key"

        valid = client.get(
            "/api/v1/operator/agents",
            headers={"x-operator-key": "test-op-key"},
        )
        assert valid.status_code == 200
        assert valid.json() == []


def test_operator_routes_list_and_results(isolated_db):
    agent_id, _, task_id = _register_and_complete_task(isolated_db)
    headers = {"x-operator-key": "test-op-key"}

    with TestClient(app) as client:
        agents_resp = client.get("/api/v1/operator/agents", headers=headers)
        assert agents_resp.status_code == 200
        agents = agents_resp.json()
        assert len(agents) == 1
        assert agents[0]["agent_id"] == agent_id
        assert agents[0]["status"] == "online"

        agent_results_resp = client.get(
            f"/api/v1/operator/agents/{agent_id}/results",
            headers=headers,
        )
        assert agent_results_resp.status_code == 200
        results = agent_results_resp.json()
        assert len(results) == 1
        assert results[0]["task_id"] == task_id
        assert results[0]["parameters"] == {"text": "hello operator"}
        assert results[0]["result"] == {"text": "hello operator"}

        task_result_resp = client.get(
            f"/api/v1/operator/tasks/{task_id}/result",
            headers=headers,
        )
        assert task_result_resp.status_code == 200
        task_result = task_result_resp.json()
        assert task_result["task_id"] == task_id
        assert task_result["status"] == "completed"
        assert task_result["result"] == {"text": "hello operator"}

        unknown_agent = client.get(
            "/api/v1/operator/agents/agent-missing/results",
            headers=headers,
        )
        assert unknown_agent.status_code == 404

        unknown_task = client.get(
            "/api/v1/operator/tasks/task-missing/result",
            headers=headers,
        )
        assert unknown_task.status_code == 404


def test_check_agent_timeouts_marks_stale_agents(isolated_db, monkeypatch):
    monkeypatch.setenv("C2_AGENT_TIMEOUT", "60")
    stale_agent = register_agent(
        RegisterRequest(
            enrollment_token="development-only-token",
            agent_version="0.1.0",
            platform="linux",
            architecture="x86_64",
        ),
        db_path=isolated_db,
    )
    active_agent = register_agent(
        RegisterRequest(
            enrollment_token="development-only-token",
            agent_version="0.1.0",
            platform="linux",
            architecture="x86_64",
        ),
        db_path=isolated_db,
    )

    old_timestamp = (datetime.now(UTC) - timedelta(seconds=120)).isoformat()
    with get_db(isolated_db) as conn:
        conn.execute(
            "UPDATE agents SET last_seen_at = ? WHERE agent_id = ?",
            (old_timestamp, stale_agent.agent_id),
        )

    updated = check_agent_timeouts(db_path=isolated_db)
    assert updated == 1

    with get_db(isolated_db) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status FROM agents WHERE agent_id = ?",
            (stale_agent.agent_id,),
        )
        assert cursor.fetchone()["status"] == "timed_out"

        cursor.execute(
            "SELECT status FROM agents WHERE agent_id = ?",
            (active_agent.agent_id,),
        )
        assert cursor.fetchone()["status"] == "online"

    # Polling again restores online status
    poll_for_tasks(
        PollRequest(
            agent_id=stale_agent.agent_id,
            session_token=stale_agent.session_token,
        ),
        db_path=isolated_db,
    )
    with get_db(isolated_db) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status FROM agents WHERE agent_id = ?",
            (stale_agent.agent_id,),
        )
        assert cursor.fetchone()["status"] == "online"


def test_cli_print_helpers_and_loop(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("x-operator-key") == "test-op-key"
        if request.url.path == "/api/v1/operator/agents":
            return httpx.Response(
                200,
                json=[
                    {
                        "agent_id": "agent-123",
                        "status": "online",
                        "platform": "linux",
                        "last_seen_at": "2026-11-25T18:00:00+00:00",
                    }
                ],
            )
        if request.url.path == "/api/v1/operator/agents/agent-123/results":
            return httpx.Response(
                200,
                json=[
                    {
                        "task_id": "task-456",
                        "task_type": "echo",
                        "status": "completed",
                        "result": {"text": "hi"},
                        "error": None,
                    }
                ],
            )
        return httpx.Response(404, json={"detail": "Not found"})

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        cli_main,
        "make_client",
        lambda api_key: httpx.Client(
            base_url="http://testserver",
            headers={"x-operator-key": api_key},
            transport=transport,
        ),
    )

    commands = iter(["help", "agents", "results agent-123", "bogus", "exit"])
    monkeypatch.setattr("builtins.input", lambda _: next(commands))

    buf = io.StringIO()
    with redirect_stdout(buf):
        cli_main.run_cli("test-op-key")

    output = buf.getvalue()
    assert "C2 Operator CLI" in output
    assert "Commands:" in output
    assert "agent-123" in output
    assert "task-456" in output
    assert json.dumps({"text": "hi"}, indent=4) in output
    assert "Unknown command." in output
