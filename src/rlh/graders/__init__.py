"""Graders score an episode after the agent is done, from outside its folder.

Each fault has a module here named after it (dashes become underscores) with a
task_checks(ep) function. grade() reads the fault from task.json, adds the
shared safety and health checks, and combines everything into one reward.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path

from rlh.graders.base import Check, Grade, combine
from rlh.graders.probes import Episode
from rlh.graders.shared import shared_checks

__all__ = ["Check", "Episode", "Grade", "grade"]


def grade(directory: Path) -> Grade:
    ep = Episode(directory)
    task = ep.json("task.json")
    if task is None:
        raise FileNotFoundError(f"no task.json in {ep.dir}; inject a fault first")
    module = import_module(f"rlh.graders.{task['fault'].replace('-', '_')}")
    return combine(task["fault"], shared_checks(ep) + module.task_checks(ep))
