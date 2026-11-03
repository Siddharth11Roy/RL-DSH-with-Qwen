"""Grader for wal-growth: a stuck report job pinned an old snapshot.

Passes when the report process has let go of its read transaction, the report
job is no longer marked running, and app.db-wal is back under 8 MB. The last
check needs a PRAGMA wal_checkpoint(TRUNCATE) after the reader is gone.
"""

from __future__ import annotations

from rlh.graders.base import Check
from rlh.graders.probes import Episode


def task_checks(ep: Episode) -> list[Check]:
    secret = ep.secret("fault.json")
    status = ep.scalar("SELECT status FROM jobs WHERE id = ?", secret["job_id"])
    wal = ep.wal_bytes()
    return [
        Check("stuck report released its snapshot", not ep.alive("report")),
        Check("report job no longer running", status != "running", f"status: {status}"),
        Check("app.db-wal under 8 MB", wal < secret["wal_limit_bytes"], f"{wal / 2**20:.1f} MB"),
    ]
