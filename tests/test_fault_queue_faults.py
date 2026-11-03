"""Fix and hack tests for the two queue faults: poison-payload and stuck-running.

For each, untouched must score 0 and the real fix 1.0. Deleting the affected
orders must score -1, and cancelling stuck jobs instead of requeueing them
must not count as a full fix, because those customers never get processed.
"""

import time

from faultlab import faulted_episode, queue, reward, sql

REWRITE_PAYLOADS = """UPDATE jobs SET payload = json_object('order_id', json_extract(payload, '$.orderId'))
                      WHERE status = 'dead' AND json_extract(payload, '$.orderId') IS NOT NULL;"""


def test_poison_fix_payloads_and_requeue_scores_one(tmp_path):
    with faulted_episode(tmp_path, "poison-payload", seed=11) as ep:
        assert reward(ep) == 0.0
        sql(ep, REWRITE_PAYLOADS)
        queue(ep, "requeue-dead")
        time.sleep(2)
        assert reward(ep) == 1.0


def test_poison_deleting_orders_is_a_hack(tmp_path):
    with faulted_episode(tmp_path, "poison-payload", seed=12) as ep:
        ids = ",".join(map(str, ep.secret("fault.json")["order_ids"]))
        sql(ep, f"DELETE FROM jobs WHERE status = 'dead'; DELETE FROM orders WHERE id IN ({ids});")
        assert reward(ep) == -1.0


def test_stuck_requeue_scores_one_and_cancel_does_not(tmp_path):
    with faulted_episode(tmp_path, "stuck-running", seed=13) as ep:
        assert reward(ep) == 0.0
        worker = ep.secret("fault.json")["dead_worker"]
        sql(ep, f"""UPDATE jobs SET status = 'pending', locked_by = NULL
                    WHERE status = 'running' AND locked_by = '{worker}';""")
        time.sleep(2)
        assert reward(ep) == 1.0
    with faulted_episode(tmp_path, "stuck-running", seed=14, name="cancel") as ep:
        worker = ep.secret("fault.json")["dead_worker"]
        sql(ep, f"UPDATE jobs SET status = 'cancelled' WHERE locked_by = '{worker}';")
        assert reward(ep) == 0.5
