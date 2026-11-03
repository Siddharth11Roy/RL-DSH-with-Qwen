"""Model backends: anything that turns chat messages into one assistant turn.

OpenAIBackend talks to any OpenAI-compatible server, which covers teacher APIs
and Qwen served locally by vLLM. ScriptedBackend replays fixed moves, so the
loop, tools and graders can be tested end to end without any model at all.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str


@dataclass
class AssistantTurn:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)

    def to_message(self) -> dict[str, Any]:
        message: dict[str, Any] = {"role": "assistant", "content": self.content or ""}
        if self.tool_calls:
            message["tool_calls"] = [
                {"id": c.id, "type": "function",
                 "function": {"name": c.name, "arguments": c.arguments}}
                for c in self.tool_calls
            ]
        return message


class Backend(Protocol):
    name: str

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> AssistantTurn:
        ...


class OpenAIBackend:
    def __init__(self, model: str, base_url: str, api_key_env: str = "RLH_API_KEY",
                 temperature: float = 0.2, max_tokens: int = 512,
                 extra_body: dict[str, Any] | None = None) -> None:
        from openai import OpenAI

        self.name = model
        self.client = OpenAI(base_url=base_url, api_key=os.environ.get(api_key_env, "not-needed"))
        self.options = {"temperature": temperature, "max_tokens": max_tokens,
                        "extra_body": extra_body or {}}

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> AssistantTurn:
        response = self.client.chat.completions.create(
            model=self.name, messages=messages, tools=tools, tool_choice="auto", **self.options)
        message = response.choices[0].message
        calls = [ToolCall(c.id, c.function.name, c.function.arguments or "{}")
                 for c in (message.tool_calls or [])]
        return AssistantTurn(message.content, calls)


class ScriptedBackend:
    def __init__(self, moves: list[tuple[str, dict[str, Any]] | str], name: str = "scripted") -> None:
        self.name = name
        self.moves = list(moves)
        self.calls = 0

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> AssistantTurn:
        move = self.moves[self.calls] if self.calls < len(self.moves) else "I am out of ideas."
        self.calls += 1
        if isinstance(move, str):
            return AssistantTurn(move)
        tool, args = move
        return AssistantTurn(None, [ToolCall(f"call_{self.calls}", tool, json.dumps(args))])
