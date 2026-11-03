"""The agent's turn loop: ask the model, run one tool, feed the result back.

Each turn allows exactly one tool call. A reply with no call, invalid JSON
arguments or an unknown tool still uses up the turn, which is the pressure that
teaches a small model the format. The loop ends on finish or at max_turns.
"""

from __future__ import annotations

import json
import time
from typing import Any

from rlh.agent.backends import Backend, BackendError, ToolCall
from rlh.agent.prompts import NUDGE, opening_messages
from rlh.agent.specs import TOOL_SPECS
from rlh.agent.tools import Toolbox, ToolError
from rlh.agent.trajectory import Step, Trajectory

SKIPPED = "skipped: only one tool call is allowed per turn"


def execute(toolbox: Toolbox, call: ToolCall) -> tuple[dict[str, Any] | None, str, str | None]:
    try:
        args = json.loads(call.arguments or "{}")
    except ValueError as exc:
        return None, f"error: invalid arguments: {exc}", "invalid arguments"
    if not isinstance(args, dict):
        return None, "error: invalid arguments: must be a JSON object", "invalid arguments"
    try:
        return args, toolbox.run(call.name, args), None
    except ToolError as exc:
        return args, f"error: {exc}", str(exc)


def run_agent(backend: Backend, toolbox: Toolbox, task: dict[str, Any],
              max_turns: int) -> Trajectory:
    traj = Trajectory(task=task, model=backend.name,
                      messages=opening_messages(task["alert"], max_turns))
    started = time.perf_counter()
    for turn in range(1, max_turns + 1):
        tick = time.perf_counter()
        try:
            reply = backend.complete(traj.messages, TOOL_SPECS)
        except (BackendError, OSError) as exc:
            traj.ended = f"backend error: {exc}"
            break
        traj.messages.append(reply.to_message())
        if not reply.tool_calls:
            traj.messages.append({"role": "user", "content": NUDGE})
            traj.steps.append(Step(turn, None, None, reply.content or "", "no tool call"))
            continue
        call, *extra = reply.tool_calls
        args, output, error = execute(toolbox, call)
        traj.messages.append({"role": "tool", "tool_call_id": call.id, "content": output})
        for other in extra:
            traj.messages.append({"role": "tool", "tool_call_id": other.id, "content": SKIPPED})
        traj.steps.append(Step(turn, call.name, args, output, error,
                               round(time.perf_counter() - tick, 2)))
        if call.name == "finish" and error is None:
            traj.ended = "finished"
            traj.summary = (args or {}).get("summary")
            break
    else:
        traj.ended = "max_turns"
    traj.seconds = time.perf_counter() - started
    return traj
