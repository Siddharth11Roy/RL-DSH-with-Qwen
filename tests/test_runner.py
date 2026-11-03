"""End-to-end test: a scripted agent fixes wal-growth through the full runner.

Creates the episode, injects the fault, plays the reference solution in
examples/solutions, grades it live, stops everything and saves the trajectory.
Checks the reward, the index line and that the saved chat is valid for training.
"""

import json

from rlh.agent.backends import ScriptedBackend
from rlh.config import ROOT, load_config
from rlh.runner import load_script, run_incident

SOLUTION = ROOT / "examples" / "solutions" / "wal-growth.json"


def test_reference_solution_scores_one_and_is_saved(tmp_path):
    config = load_config()
    config["world"]["runs_dir"] = str(tmp_path)
    backend = ScriptedBackend(load_script(SOLUTION))
    traj = run_incident(backend, "wal-growth", seed=21, config=config)

    assert traj.ended == "finished"
    assert traj.reward == 1.0

    saved = list((tmp_path / "trajectories").glob("wal-growth-s21-*.json"))
    assert len(saved) == 1
    data = json.loads(saved[0].read_text(encoding="utf-8"))
    roles = [m["role"] for m in data["messages"]]
    assert roles[:2] == ["system", "user"]
    calls = [m for m in data["messages"] if m.get("tool_calls")]
    answers = {m["tool_call_id"] for m in data["messages"] if m["role"] == "tool"}
    assert {c["tool_calls"][0]["id"] for c in calls} == answers

    index = (tmp_path / "trajectories" / "index.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(index[-1])["reward"] == 1.0
