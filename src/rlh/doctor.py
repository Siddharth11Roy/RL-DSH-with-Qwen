"""Environment checks behind `rlh doctor`.

Each check returns a Check: a name, pass or fail, a one-line detail, and
whether it is required. Required checks block the project today; optional
ones (GPU, WSL2, DeepSeek Harness) only matter for later phases.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIN_NODE = (22, 13)


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    required: bool = True


def _run(cmd: list[str]) -> tuple[int, str]:
    try:
        out = subprocess.run(cmd, check=False, capture_output=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    raw = out.stdout or out.stderr
    text = raw.decode("utf-16-le", "ignore") if b"\x00" in raw else raw.decode("utf-8", "ignore")
    return out.returncode, text.strip()


def check_python() -> Check:
    return Check("Python >= 3.11", sys.version_info >= (3, 11), platform.python_version())


def check_tool(name: str, required: bool = True) -> Check:
    path = shutil.which(name)
    if not path:
        return Check(name, False, "not found on PATH", required)
    code, out = _run([path, "--version"])
    return Check(name, code == 0, out.splitlines()[0] if out else "", required)


def check_node() -> Check:
    label = f"Node >= {MIN_NODE[0]}.{MIN_NODE[1]} (node:sqlite)"
    if not shutil.which("node"):
        return Check(label, False, "not found on PATH")
    _, out = _run(["node", "--version"])
    parts = out.lstrip("v").split(".")
    version = tuple(int(p) for p in parts[:2]) if len(parts) >= 2 else (0, 0)
    return Check(label, version >= MIN_NODE, out)


def check_gpu() -> Check:
    if not shutil.which("nvidia-smi"):
        return Check("NVIDIA GPU", False, "nvidia-smi not found", False)
    query = ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"]
    code, out = _run(query)
    if code != 0 or "," not in out:
        return Check("NVIDIA GPU", False, out or "no GPU reported", False)
    name, mem = out.splitlines()[0].rsplit(",", 1)
    return Check("NVIDIA GPU", True, f"{name.strip()}, {int(mem) / 1024:.0f} GB", False)


def check_wsl() -> Check:
    if platform.system() != "Windows":
        return Check("WSL2 distro", True, "not needed outside Windows", False)
    code, out = _run(["wsl", "-l", "-v"])
    distros = [line for line in out.splitlines()[1:] if line.strip() and "docker" not in line]
    ok = code == 0 and any(line.split()[-1] == "2" for line in distros)
    detail = distros[0].replace("*", "").split()[0] if ok else "install Ubuntu under WSL2"
    return Check("WSL2 distro", ok, detail, False)


def check_dsh() -> Check:
    path = ROOT / "vendor" / "deepseek-harness"
    ok = (path / "package.json").exists()
    detail = "fetched" if ok else "run: uv run python scripts/fetch_dsh.py"
    return Check("DeepSeek Harness", ok, detail, False)


def run_checks() -> list[Check]:
    return [
        check_python(),
        check_tool("git"),
        check_tool("uv"),
        check_node(),
        check_tool("npm"),
        check_gpu(),
        check_wsl(),
        check_dsh(),
    ]
