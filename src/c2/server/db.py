import sqlite3
from contextlib import contextmanager
from typing import Generator

from c2.server.config import get_db_path


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Create an configure a SQLite connection with WAL mode and foreign keys. """
    target_path = db_path if db_path is not None else get_db_path()
    conn = sqlite3.connect(target_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=5000;")

    if target_path != ":memory:":
        conn.execute("PRAGMA journal_mode=WAL;")

    return conn


@contextmanager

def get_db(db_path: str | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite connections handling transactions and cleanup."""
    conn = get_connection(db_path)
    try: 
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str | None = None) -> None:
    """Create tables and indexes if they do not exist."""
    with get_db(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                session_token_hash TEXT NOT NULL,
                platform TEXT NOT NULL,
                architecture TEXT NOT NULL,
                registered_at TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'online'
            );

            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL, REFERENCES agents(agent_id) ON DELETE CASCADE,
                task_type TEXT NOT NULL,
                parameters TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                dispatched_at TEXT,
                completed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                agent_id TEXT,
                details TEXT,
                ip_address TEXT
                );

            CREATE INDEX IF NOT EXISTS idx_tasks_agent_status ON tasks(agent_id, status);
            CREATE INDEX IF NOT EXISTS idx_agents_last_seen ON agents(last_seen);
            CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
        """)


def get_agents(db_path: str | None = None) -> list[sqlite3.Row]:
    """Return all agents ordered by last seen time."""
    with get_db(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT * FROM agents
            ORDER BY last_seen DESC NULLS LAST, created_at DESC
            """)
        return cursor.fetchall()