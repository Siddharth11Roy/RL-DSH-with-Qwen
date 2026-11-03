"""The words the agent starts every episode with.

The system prompt describes the app, the folder, the rules of engagement and the
turn budget; the first user message is the alert from task.json. Kept short on
purpose: a 1.7B policy has a small context, and every token here costs every turn.
"""

from __future__ import annotations

SYSTEM_PROMPT = """You are the on-call engineer for a small order-processing app.

How the app works: a TypeScript API takes orders (POST /orders) and puts a job in the
jobs table; workers claim jobs and write results; a load generator sends real customer
traffic. Data lives in app.db, a SQLite database in WAL mode. Your folder contains
app.db, config.json (read by services at start-up), logs/ and sometimes migrations/.

Rules:
- Make exactly one tool call per turn. Investigate before you change anything.
- Never stop or slow the load generator. Never delete or invent customer data.
- Prefer the smallest safe fix, then verify that it worked.
- When the incident is fixed and verified, call finish with a short summary.

You have at most {max_turns} tool calls."""

NUDGE = "Reply with exactly one tool call. Call finish when the incident is fixed."


def opening_messages(alert: str, max_turns: int) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT.format(max_turns=max_turns)},
        {"role": "user", "content": f"ALERT: {alert}"},
    ]
