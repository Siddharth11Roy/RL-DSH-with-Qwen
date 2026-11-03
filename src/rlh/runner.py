"""Runs one full incident: create an episode, break it, let the agent work, grade it.

Grading happens while the services are still live (the graders probe the API,
logs and processes), after a short settle time; then everything is stopped and
the trajectory is saved under runs/trajectories with its reward.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from rlh.agent.backends import Backend
from rlh.agent.loop import run_agent
from rlh.agent.tools import Toolbox
from rlh.agent.trajectory import Trajectory
from rlh.config import ROOT
from rlh.graders import grade
from rlh.world import inject_fault, run_episode


def run_incident(backend: Backend, fault: str, seed: int, config: dict[str, Any],
                 rows: int = 800, rate: int = 15) -> Trajectory:
    runs = ROOT / config["world"]["runs_dir"]
    directory = runs / f"{fault}-s{seed}"
    harness = config["harness"]
    run_episode("create", directory, "--rows", str(rows), "--seed", str(seed))
    run_episode("start", directory, "--rate", str(rate))
    try:
        inject_fault(directory, fault, seed)
        task = {**json.loads((directory / "task.json").read_text(encoding="utf-8")), "seed": seed}
        toolbox = Toolbox(directory, harness["tool_output_chars"], harness["tool_timeout_s"])
        traj = run_agent(backend, toolbox, task, harness["max_turns"])
        time.sleep(harness.get("settle_s", 3))
        traj.grade = grade(directory).to_dict()
    finally:
        run_episode("stop", directory)
    traj.save(runs / "trajectories")
    return traj


def load_script(path: Path) -> list[Any]:
    moves = json.loads(path.read_text(encoding="utf-8"))
    return [move if isinstance(move, str) else (move[0], move[1]) for move in moves]
