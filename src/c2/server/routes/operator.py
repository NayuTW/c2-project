import json

from fastapi import APIRouter, Depends, HTTPException

from c2.server.db import get_db
from c2.server.dependencies import require_operator

router = APIRouter(
    prefix="/api/v1/operator",
    tags=["operator"],
    dependencies=[Depends(require_operator)],
)


@router.get("/agents")
def list_agents() -> list[dict]:
    """Return all registered agents ordered by registration time."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT agent_id, platform, architecture, agent_version, "
            "registered_at, last_seen_at, status FROM agents ORDER BY registered_at DESC"
        )
        rows = cursor.fetchall()
    return [dict(row) for row in rows]


@router.get("/agents/{agent_id}/results")
def get_agent_results(agent_id: str) -> list[dict]:
    """Return all tasks and any submitted results for a specific agent."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT agent_id FROM agents WHERE agent_id = ?", (agent_id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Unknown agent")

        cursor.execute(
            """
            SELECT t.task_id, t.task_type, t.parameters, t.status,
                   t.created_at, t.dispatched_at, t.completed_at,
                   tr.result, tr.error, tr.received_at
            FROM tasks t
            LEFT JOIN task_results tr ON t.task_id = tr.task_id
            WHERE t.agent_id = ?
            ORDER BY t.created_at DESC
            """,
            (agent_id,),
        )
        rows = cursor.fetchall()

    results = []
    for row in rows:
        r = dict(row)
        if r["parameters"]:
            r["parameters"] = json.loads(r["parameters"])
        if r["result"]:
            r["result"] = json.loads(r["result"])
        results.append(r)
    return results


@router.get("/tasks/{task_id}/result")
def get_task_result(task_id: str) -> dict:
    """Return the status and result for a single task."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT t.task_id, t.task_type, t.status, t.completed_at,
                   tr.result, tr.error, tr.received_at
            FROM tasks t
            LEFT JOIN task_results tr ON t.task_id = tr.task_id
            WHERE t.task_id = ?
            """,
            (task_id,),
        )
        row = cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Unknown task")

    r = dict(row)
    if r["result"]:
        r["result"] = json.loads(r["result"])
    return r
