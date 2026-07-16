"""Loads and validates the agent task suite under data/.

Schema (Option A): each task carries `id`, `dimension`, `task`, plus optional
`expects` hints and `notes`. Oracles live in test code, never in the data.
`task` is the agent's input: a string for single-turn tasks, a list of user
turns for a multi_turn task - both non-empty, so the required-field check
accepts either.
"""

from pathlib import Path

import yaml

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DIMENSIONS = {"outcome", "trajectory", "tool_use", "multi_turn", "excessive_agency"}
_REQUIRED = ("id", "dimension", "task")


def load_tasks(path: Path | None = None) -> list[dict]:
    path = path or DATA_DIR
    tasks: list[dict] = []
    for f in sorted(Path(path).glob("*.yaml")):
        with open(f) as fh:
            doc = yaml.safe_load(fh)
        for task in doc if isinstance(doc, list) else [doc] if doc else []:
            _validate(task, f)
            tasks.append(task)
    ids = [t["id"] for t in tasks]
    if len(ids) != len(set(ids)):
        raise ValueError(
            f"duplicate task ids in {path}: {sorted(set(i for i in ids if ids.count(i) > 1))}"
        )
    return tasks


def get_task(task_id: str, path: Path | None = None) -> dict:
    """Fetch one task by id, so tests share the YAML task string instead of
    hardcoding a copy that can drift."""
    for task in load_tasks(path):
        if task["id"] == task_id:
            return task
    raise KeyError(f"no task with id {task_id!r} under {path or DATA_DIR}")


def _validate(task: dict, source: Path) -> None:
    missing = [k for k in _REQUIRED if not task.get(k)]
    if missing:
        raise ValueError(f"{source}: task {task.get('id', '?')!r} missing fields {missing}")
    if task["dimension"] not in DIMENSIONS:
        raise ValueError(
            f"{source}: task {task['id']!r} has unknown dimension {task['dimension']!r} "
            f"(expected one of {sorted(DIMENSIONS)})"
        )
