"""Tool definitions the model sees, in OpenAI function-calling format.

The same schemas go to API teachers and to Qwen served by vLLM, so trajectories
from both share one format. Tools mirror what an on-call engineer has: a shell,
SQL, logs, the job queue, service control, file read/edit, and a finish call.
"""

from __future__ import annotations

from typing import Any


def _tool(name: str, description: str, /, **params: tuple[str, str, bool]) -> dict[str, Any]:
    properties = {key: {"type": kind, "description": desc} for key, (kind, desc, _) in params.items()}
    required = [key for key, (_, _, needed) in params.items() if needed]
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": properties, "required": required},
    }}


TOOL_SPECS: list[dict[str, Any]] = [
    _tool("shell", "Run a bash command in the app's folder. 30 s timeout.",
          command=("string", "the command to run", True)),
    _tool("sql", "Run one SQL statement (SELECT, PRAGMA, UPDATE, ...) against app.db.",
          query=("string", "a single SQL statement", True)),
    _tool("logs", "Show the last lines of a service log (api, worker1, load, ...).",
          service=("string", "service name, e.g. api or worker1", True),
          lines=("integer", "how many lines, default 30", False)),
    _tool("queue", "Job queue: stats | list [status] | show <id> | cancel <id> | requeue-dead.",
          command=("string", "stats, list, show, cancel or requeue-dead", True),
          arg=("string", "status or job id, when the command needs one", False)),
    _tool("svc", "Services: status | start <name> | stop <name> | restart <name|all>.",
          command=("string", "status, start, stop or restart", True),
          name=("string", "api, workerN or all", False)),
    _tool("read_file", "Read a text file inside the app's folder.",
          path=("string", "path relative to the app's folder", True)),
    _tool("edit_file", "Replace one exact occurrence of old with new in a file.",
          path=("string", "path relative to the app's folder", True),
          old=("string", "exact text to replace", True),
          new=("string", "replacement text", True)),
    _tool("finish", "Call when the incident is fixed and verified, with a short summary.",
          summary=("string", "what was wrong and what you changed", True)),
]

TOOL_NAMES = [spec["function"]["name"] for spec in TOOL_SPECS]
