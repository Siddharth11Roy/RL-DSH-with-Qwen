"""Tests for the agent turn loop with scripted backends, no model needed.

Checks that finish ends the episode, that plain text and malformed arguments
still use up a turn, that extra tool calls in one reply are answered as skipped,
that the turn budget is enforced, and that a crashing backend ends the episode.
"""

import pytest

from rlh.agent.backends import AssistantTurn, ScriptedBackend, ToolCall
from rlh.agent.loop import SKIPPED, run_agent
from rlh.agent.tools import Toolbox
from rlh.world import run_episode

TASK = {"fault": "demo", "seed": 1, "alert": "something is wrong"}


@pytest.fixture(scope="module")
def box(tmp_path_factory):
    directory = tmp_path_factory.mktemp("loop") / "ep"
    run_episode("create", directory, "--rows", "20", "--seed", "1")
    return Toolbox(directory)


class FixedBackend:
    name = "fixed"

    def __init__(self, turn: AssistantTurn) -> None:
        self.turn = turn

    def complete(self, messages, tools):
        return self.turn


def test_finish_ends_the_episode(box):
    backend = ScriptedBackend([("sql", {"query": "SELECT 1"}), ("finish", {"summary": "done"})])
    traj = run_agent(backend, box, TASK, max_turns=5)
    assert traj.ended == "finished" and traj.summary == "done"
    assert [s.tool for s in traj.steps] == ["sql", "finish"]
    assert traj.messages[0]["role"] == "system" and "ALERT" in traj.messages[1]["content"]


def test_plain_text_uses_a_turn_and_gets_nudged(box):
    traj = run_agent(ScriptedBackend(["let me think", ("finish", {"summary": "ok"})]), box, TASK, 5)
    assert traj.steps[0].error == "no tool call"
    assert traj.messages[3] == {"role": "user", "content": traj.messages[3]["content"]}
    assert traj.ended == "finished"


def test_invalid_json_arguments_are_reported(box):
    backend = FixedBackend(AssistantTurn(None, [ToolCall("c1", "sql", "{not json")]))
    traj = run_agent(backend, box, TASK, max_turns=2)
    assert traj.ended == "max_turns"
    assert all(s.error == "invalid arguments" for s in traj.steps)


def test_extra_tool_calls_are_skipped(box):
    calls = [ToolCall("a", "sql", '{"query": "SELECT 1"}'), ToolCall("b", "logs", '{"service": "api"}')]
    traj = run_agent(FixedBackend(AssistantTurn(None, calls)), box, TASK, max_turns=1)
    tool_messages = [m for m in traj.messages if m["role"] == "tool"]
    assert [m["tool_call_id"] for m in tool_messages] == ["a", "b"]
    assert tool_messages[1]["content"] == SKIPPED


def test_backend_error_ends_the_episode(box):
    class Broken:
        name = "broken"

        def complete(self, messages, tools):
            raise ConnectionError("server down")

    traj = run_agent(Broken(), box, TASK, max_turns=3)
    assert traj.ended.startswith("backend error") and not traj.steps
