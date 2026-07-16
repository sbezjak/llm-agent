"""The task suite loads, validates, and is fetchable by id. Malformed tasks
must fail loudly at load time, not silently skip - a task that never runs is
a finding that never gets locked in."""

import pytest

from llm_agent.dataset import DIMENSIONS, get_task, load_tasks

pytestmark = pytest.mark.mocked


def test_suite_loads_and_validates():
    tasks = load_tasks()
    assert tasks, "data/ contains no tasks"
    assert all(t["dimension"] in DIMENSIONS for t in tasks)


def test_get_task_by_id():
    task = get_task("multi-tool-dependency")
    assert "cities.txt" in task["task"]


def test_malformed_task_fails_loudly(tmp_path):
    (tmp_path / "bad.yaml").write_text("- id: no-dimension\n  task: 'do a thing'\n")
    with pytest.raises(ValueError, match="missing fields"):
        load_tasks(tmp_path)


def test_unknown_dimension_fails_loudly(tmp_path):
    (tmp_path / "bad.yaml").write_text("- id: x\n  dimension: vibes\n  task: 'do a thing'\n")
    with pytest.raises(ValueError, match="unknown dimension"):
        load_tasks(tmp_path)
