import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_DB_PATH = str(PROJECT_ROOT / "c2.db")


def get_db_path() -> str:
    """Return configured SQLite DB file path or default."""
    return os.getenv("C2_DB_PATH", DEFAULT_DB_PATH)


def get_enrollment_token() -> str:
    """Return enrollment token required for agent registration."""
    return os.getenv("C2_ENROLLMENT_TOKEN", "development-only-token")


def get_default_poll_interval() -> int:
    """Return default polling interval in seconds. """
    return int(os.getenv("C2_POLL_INTERVAL", "10"))
