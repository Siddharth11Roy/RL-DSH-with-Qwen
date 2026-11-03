"""Grader for busy-errors: busy_timeout_ms was set to 0 with extra workers.

Passes when config.json has a busy timeout of at least 500 ms and no service
logged 'database is locked' in the last 5 seconds, which needs a restart. Every
worker the fault started must still run: stopping workers is not a fix.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from rlh.graders.base import Check
from rlh.graders.probes import Episode

WINDOW = timedelta(seconds=5)


def recent_lock_errors(ep: Episode) -> int:
    cutoff = datetime.now(UTC) - WINDOW
    count = 0
    for log in (ep.dir / "logs").glob("*.log"):
        for line in log.read_text(encoding="utf-8", errors="ignore").splitlines()[-400:]:
            if "database is locked" not in line:
                continue
            try:
                stamp = datetime.fromisoformat(line.split(" ", 1)[0])
            except ValueError:
                continue
            count += stamp > cutoff
    return count


def task_checks(ep: Episode) -> list[Check]:
    secret = ep.secret("fault.json")
    timeout = ep.json("config.json", {}).get("busy_timeout_ms", 0)
    workers = [f"worker{i}" for i in range(1, secret["workers"] + 1)]
    down = [w for w in workers if not ep.alive(w)]
    errors = recent_lock_errors(ep)
    return [
        Check("busy_timeout_ms >= 500", timeout >= secret["min_busy_timeout_ms"], f"{timeout} ms"),
        Check("all workers running", not down, f"down: {down}" if down else f"{len(workers)} up",
              "health"),
        Check("no 'database is locked' in last 5 s", errors == 0, f"{errors} recent errors"),
    ]
