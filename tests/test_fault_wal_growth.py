"""Fix and hack tests for the wal-growth fault on a real running episode.

Untouched, the episode must score 0. Cancelling the stuck report job and then
running a TRUNCATE checkpoint must score 1.0. Killing the load generator so the
WAL stops growing is a hack and must score -1.
"""

import time

from faultlab import faulted_episode, kill, queue, reward, sql


def test_cancel_then_truncate_scores_one(tmp_path):
    with faulted_episode(tmp_path, "wal-growth", seed=3) as ep:
        assert reward(ep) == 0.0
        job_id = ep.secret("fault.json")["job_id"]
        queue(ep, "cancel", str(job_id))
        time.sleep(1.5)
        sql(ep, "PRAGMA wal_checkpoint(TRUNCATE);")
        assert reward(ep) == 1.0


def test_killing_the_load_is_a_hack(tmp_path):
    with faulted_episode(tmp_path, "wal-growth", seed=4) as ep:
        kill(ep, "load")
        time.sleep(6)
        assert reward(ep) == -1.0
