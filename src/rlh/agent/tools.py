"""Executes the agent's tool calls inside one episode folder.

Every tool runs with the episode folder as its root: file paths may not leave
it, nothing may touch the grader's .secret folder, and every output is cut to
a fixed size (head and tail kept) so one noisy command cannot flood the context.
"""

from __future__ import annotations

import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

from rlh.world import WorldError, run_node

SECRET_MARK = ".secret"


class ToolError(Exception):
    pass


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    head, tail = text[: limit * 2 // 3], text[-limit // 3:]
    return f"{head}\n...[{len(text) - len(head) - len(tail)} chars cut]...\n{tail}"


class Toolbox:
    def __init__(self, episode_dir: Path, output_chars: int = 1500, timeout_s: int = 30) -> None:
        self.root = Path(episode_dir).resolve()
        self.output_chars = output_chars
        self.timeout_s = timeout_s

    def run(self, name: str, args: dict[str, Any]) -> str:
        handler = getattr(self, f"tool_{name}", None)
        if handler is None:
            raise ToolError(f"unknown tool: {name}")
        try:
            return truncate(handler(**args).strip() or "(no output)", self.output_chars)
        except TypeError as exc:
            raise ToolError(f"bad arguments for {name}: {exc}") from exc

    def _path(self, relative: str) -> Path:
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root) or SECRET_MARK in str(path):
            raise ToolError(f"path is outside the app's folder: {relative}")
        return path

    def tool_shell(self, command: str) -> str:
        if SECRET_MARK in command:
            raise ToolError("that path is not available")
        bash = shutil.which("bash") or "/bin/bash"
        try:
            out = subprocess.run([bash, "-c", command], cwd=self.root, capture_output=True,
                                 text=True, timeout=self.timeout_s, check=False)
        except subprocess.TimeoutExpired:
            return f"timed out after {self.timeout_s} s"
        return f"{out.stdout}{out.stderr}\n[exit {out.returncode}]"

    def tool_sql(self, query: str) -> str:
        conn = sqlite3.connect(self.root / "app.db", timeout=5, isolation_level=None)
        try:
            cursor = conn.execute(query)
            if cursor.description is None:
                return f"ok, {cursor.rowcount} rows changed" if cursor.rowcount >= 0 else "ok"
            header = " | ".join(col[0] for col in cursor.description)
            rows = cursor.fetchmany(51)
            lines = [" | ".join(map(str, row)) for row in rows[:50]]
            more = "\n(more rows not shown)" if len(rows) > 50 else ""
            return "\n".join([header, *lines]) + more if lines else f"{header}\n(0 rows)"
        except sqlite3.Error as exc:
            return f"SQL error: {exc}"
        finally:
            conn.close()

    def tool_logs(self, service: str, lines: int = 30) -> str:
        log = self._path(f"logs/{service}.log")
        if not log.exists():
            known = ", ".join(p.stem for p in (self.root / "logs").glob("*.log"))
            return f"no log for {service}; available: {known}"
        return "\n".join(log.read_text(encoding="utf-8", errors="ignore").splitlines()[-lines:])

    def _world(self, script: str, *args: str) -> str:
        try:
            return run_node(script, str(self.root), *args)
        except WorldError as exc:
            return f"error: {exc}"

    def tool_queue(self, command: str, arg: str | None = None) -> str:
        return self._world("queue-cli.ts", command, *([arg] if arg else []))

    def tool_svc(self, command: str, name: str | None = None) -> str:
        return self._world("svc-cli.ts", command, *([name] if name else []))

    def tool_read_file(self, path: str) -> str:
        target = self._path(path)
        if not target.is_file():
            return f"no such file: {path}"
        return target.read_text(encoding="utf-8", errors="ignore")

    def tool_edit_file(self, path: str, old: str, new: str) -> str:
        target = self._path(path)
        text = target.read_text(encoding="utf-8") if target.is_file() else ""
        if text.count(old) != 1:
            return f"edit failed: old text found {text.count(old)} times, it must appear exactly once"
        target.write_text(text.replace(old, new), encoding="utf-8")
        return f"edited {path}"

    def tool_finish(self, summary: str) -> str:
        return f"finished: {summary}"
