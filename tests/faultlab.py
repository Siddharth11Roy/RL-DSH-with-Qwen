"""Helpers for fault tests: run a real episode, inject a fault, act, grade.

faulted_episode() creates and starts an episode in a temp folder, injects the
fault and always stops every process afterwards. sql(), svc() and edit_config()
are the same moves the agent will make, used here to script fixes and hacks.
"""

from __future__ import annotations

import json
import os
import signal
import sqlite3
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from rlh.graders import Episode, grade
from rlh.world import inject_fault, run_episode, run_node


@contextmanager
def faulted_episode(tmp: Path, fault: str, seed: int = 1, rows: int = 800,
                    rate: int = 15) -> Iterator[Episode]:
    directory = tmp / "ep"
    run_episode("create", directory, "--rows", str(rows), "--seed", str(seed))
    run_episode("start", directory, "--rate", str(rate))
    try:
        inject_fault(directory, fault, seed)
        yield Episode(directory)
    finally:
        run_episode("stop", directory)


def sql(ep: Episode, script: str) -> None:
    with sqlite3.connect(ep.dir / "app.db", timeout=10) as conn:
        conn.executescript(script)


def svc(ep: Episode, *args: str) -> str:
    return run_node("svc-cli.ts", str(ep.dir), *args)


def queue(ep: Episode, *args: str) -> str:
    return run_node("queue-cli.ts", str(ep.dir), *args)


def edit_config(ep: Episode, **changes: object) -> None:
    path = ep.dir / "config.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps({**config, **changes}, indent=2), encoding="utf-8")


def kill(ep: Episode, service: str) -> None:
    pid = ep.pids()[service]
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False, capture_output=True)
    else:
        os.kill(pid, signal.SIGKILL)


def reward(ep: Episode) -> float:
    return grade(ep.dir).reward
