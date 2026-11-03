"""Tests for the agent's toolbox on a created (not running) episode.

Covers SQL reads and writes, log tails, exact-match file edits, output
truncation, and the guards: no paths outside the folder, no access to the
grader's .secret folder, and a clear error for unknown tools or arguments.
"""

import pytest

from rlh.agent.specs import TOOL_NAMES
from rlh.agent.tools import Toolbox, ToolError, truncate
from rlh.world import run_episode


@pytest.fixture(scope="module")
def box(tmp_path_factory):
    directory = tmp_path_factory.mktemp("tools") / "ep"
    run_episode("create", directory, "--rows", "50", "--seed", "2")
    (directory / "logs" / "worker1.log").write_text("line1\nline2\nline3\n", encoding="utf-8")
    return Toolbox(directory, output_chars=400)


def test_every_spec_has_a_handler(box):
    for name in TOOL_NAMES:
        assert hasattr(box, f"tool_{name}")


def test_sql_reads_and_writes(box):
    assert "50" in box.run("sql", {"query": "SELECT count(*) AS n FROM orders"})
    assert "rows changed" in box.run("sql", {"query": "UPDATE orders SET status = status WHERE id = 1"})
    assert box.run("sql", {"query": "SELEC nonsense"}).startswith("SQL error")


def test_logs_tail_and_missing_service(box):
    assert box.run("logs", {"service": "worker1", "lines": 2}) == "line2\nline3"
    assert "available" in box.run("logs", {"service": "nope"})


def test_edit_file_needs_exactly_one_match(box):
    assert box.run("edit_file", {"path": "config.json", "old": "2000", "new": "2500"}) == "edited config.json"
    assert "2500" in box.run("read_file", {"path": "config.json"})
    assert "found 0 times" in box.run("edit_file", {"path": "config.json", "old": "zzz", "new": "y"})


def test_guards(box):
    with pytest.raises(ToolError):
        box.run("read_file", {"path": "../ep.secret/checksum.json"})
    with pytest.raises(ToolError):
        box.run("shell", {"command": "cat ../ep.secret/checksum.json"})
    with pytest.raises(ToolError):
        box.run("teleport", {})
    with pytest.raises(ToolError):
        box.run("sql", {"sql": "SELECT 1"})


def test_shell_runs_in_the_episode_folder(box):
    assert "app.db" in box.run("shell", {"command": "ls"})


def test_truncate_keeps_head_and_tail():
    text = "a" * 500 + "b" * 500
    cut = truncate(text, 300)
    assert cut.startswith("a") and cut.endswith("b") and "chars cut" in cut
