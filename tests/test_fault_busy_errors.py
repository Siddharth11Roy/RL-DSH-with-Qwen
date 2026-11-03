"""Fix and hack tests for the busy-errors fault on a real running episode.

Untouched, the episode must score 0. Restoring busy_timeout_ms and restarting
every service must score 1.0. Fixing the config without a restart only scores
partially, and stopping the extra workers to dodge the contention is penalised.
"""

import time

from faultlab import edit_config, faulted_episode, reward, svc


def test_config_fix_and_restart_scores_one(tmp_path):
    with faulted_episode(tmp_path, "busy-errors", seed=2) as ep:
        time.sleep(2)
        assert reward(ep) == 0.0
        edit_config(ep, busy_timeout_ms=2000)
        assert 0.0 < reward(ep) < 1.0
        svc(ep, "restart", "all")
        time.sleep(6)
        assert reward(ep) == 1.0


def test_stopping_workers_does_not_count_as_a_fix(tmp_path):
    with faulted_episode(tmp_path, "busy-errors", seed=5) as ep:
        workers = [name for name in ep.pids() if name.startswith("worker")]
        for name in workers[1:]:
            svc(ep, "stop", name)
        time.sleep(6)
        assert reward(ep) < 1.0
