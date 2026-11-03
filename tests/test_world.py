"""Tests for the `rlh world` bridge to the TypeScript practice world.

Runs a real episode through create, start, status and stop in a temp folder,
so it needs node on PATH and takes a few seconds. Also checks that a failing
world command surfaces as WorldError instead of a silent empty result.
"""

import shutil
import time

import pytest

from rlh.world import WorldError, run_episode

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def test_episode_round_trip(tmp_path):
    episode = tmp_path / "ep"
    created = run_episode("create", episode, "--rows", "200", "--seed", "5")
    assert len(created["checksum"]) == 12
    assert (tmp_path / "ep.secret" / "checksum.json").exists()

    started = run_episode("start", episode, "--rate", "10")
    assert set(started["pids"]) == {"api", "worker1", "load"}
    try:
        time.sleep(2)
        status = run_episode("status", episode)
        assert all(status["processes"].values())
        assert status["api"]["queue"]["done"] >= 0
    finally:
        stopped = run_episode("stop", episode)
    assert stopped["processes"] == 3
    assert run_episode("status", episode)["processes"] == {}


def test_bad_command_raises(tmp_path):
    with pytest.raises(WorldError, match="unknown command"):
        run_episode("explode", tmp_path / "ep")
