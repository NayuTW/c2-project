import pytest

from c2.agent.handlers import execute_task


def test_unknown_task_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported task type",
    ):
        execute_task("unknown_task", {})