"""What one agent episode looked like, saved as JSON for grading and training.

A Trajectory keeps the exact chat messages sent to the model (the format SFT
and GRPO will train on), one Step per tool call for humans to read, how the
episode ended, and the grade. save() also appends a one-line summary to an index.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Step:
    turn: int
    tool: str | None
    arguments: dict[str, Any] | None
    output: str
    error: str | None = None
    seconds: float = 0.0


@dataclass
class Trajectory:
    task: dict[str, Any]
    model: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    ended: str = "running"
    summary: str | None = None
    grade: dict[str, Any] | None = None
    started_at: float = field(default_factory=time.time)
    seconds: float = 0.0

    @property
    def reward(self) -> float | None:
        return None if self.grade is None else self.grade["reward"]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def save(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(self.started_at))
        name = f"{self.task.get('fault', 'task')}-s{self.task.get('seed', 0)}-{stamp}.json"
        path = directory / name
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        summary = {"file": name, "fault": self.task.get("fault"), "seed": self.task.get("seed"),
                   "model": self.model, "reward": self.reward, "turns": len(self.steps),
                   "ended": self.ended, "seconds": round(self.seconds, 1)}
        with (directory / "index.jsonl").open("a", encoding="utf-8") as index:
            index.write(json.dumps(summary) + "\n")
        return path
