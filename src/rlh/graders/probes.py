"""Read-only views of an episode that graders use from outside its folder.

Episode wraps the folder and its sibling .secret folder: JSON files, SQLite
queries, WAL size, process liveness and API calls. checksum() repeats the
world's seed.ts hash exactly, so the two languages always agree on the data.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any


def pid_alive(pid: int) -> bool:
    if sys.platform == "win32":
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], check=False,
                             capture_output=True, text=True).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class Episode:
    def __init__(self, directory: Path) -> None:
        self.dir = Path(directory).resolve()
        self.secret_dir = Path(f"{self.dir}.secret")

    def json(self, name: str, default: Any = None) -> Any:
        path = self.dir / name
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

    def secret(self, name: str) -> Any:
        return json.loads((self.secret_dir / name).read_text(encoding="utf-8"))

    def query(self, sql: str, *args: Any) -> list[tuple]:
        with sqlite3.connect(self.dir / "app.db", timeout=5) as conn:
            return conn.execute(sql, args).fetchall()

    def scalar(self, sql: str, *args: Any) -> Any:
        rows = self.query(sql, *args)
        return rows[0][0] if rows else None

    def wal_bytes(self) -> int:
        wal = self.dir / "app.db-wal"
        return wal.stat().st_size if wal.exists() else 0

    def pids(self) -> dict[str, int]:
        return self.json("pids.json", {})

    def alive(self, service: str) -> bool:
        pid = self.pids().get(service)
        return pid is not None and pid_alive(pid)

    def api_get(self, path: str) -> tuple[int, Any]:
        port = (self.dir / "api.port").read_text().strip()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=3) as res:
                return res.status, json.loads(res.read())
        except OSError as exc:
            return 0, str(exc)

    def ledger(self) -> list[dict]:
        path = self.dir / "ledger.jsonl"
        lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
        return [json.loads(line) for line in lines if line.strip()]

    def checksum(self, rows: int) -> str:
        digest = hashlib.sha256()
        sql = """SELECT o.id, o.customer, o.amount_cents, r.total_cents
                 FROM orders o JOIN results r ON r.order_id = o.id
                 WHERE o.id <= ? ORDER BY o.id, r.id"""
        for oid, customer, amount, total in self.query(sql, rows):
            digest.update(f"{oid}|{customer}|{amount}|{total}\n".encode())
        return digest.hexdigest()
