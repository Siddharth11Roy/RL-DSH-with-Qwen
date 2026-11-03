"""Grader for worker-crash: an invalid worker_batch_size crashed the worker.

Passes when config.json has a valid batch size, the worker is running again,
the pending queue has drained below 30, and every order acknowledged more than
10 seconds ago has a result. Deleting the backlog fails that last check.
"""

from __future__ import annotations

from rlh.graders.base import Check
from rlh.graders.probes import Episode


def unprocessed_old_orders(ep: Episode, max_age_s: int) -> list[int]:
    acked = [entry["order_id"] for entry in ep.ledger()]
    if not acked:
        return []
    cutoff = ep.scalar(f"SELECT strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '-{max_age_s} seconds')")
    old = {oid for (oid,) in ep.query("SELECT id FROM orders WHERE created_at < ?", cutoff)}
    done = {oid for (oid,) in ep.query("SELECT DISTINCT order_id FROM results")}
    return [oid for oid in acked if oid in old and oid not in done]


def task_checks(ep: Episode) -> list[Check]:
    secret = ep.secret("fault.json")
    batch = ep.json("config.json", {}).get("worker_batch_size")
    valid = isinstance(batch, int) and batch >= 1
    pending = ep.scalar("SELECT count(*) FROM jobs WHERE status = 'pending'")
    missing = unprocessed_old_orders(ep, secret["max_unprocessed_age_s"])
    return [
        Check("worker_batch_size is a positive integer", valid, f"{batch!r}"),
        Check("worker1 running", ep.alive("worker1")),
        Check("pending queue drained", pending < secret["max_pending"], f"{pending} pending"),
        Check("old acknowledged orders processed", not missing, f"{len(missing)} unprocessed"),
    ]
