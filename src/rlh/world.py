"""Python bridge to the practice world, exposed as `rlh world ...`.

The world itself is TypeScript; this module only calls its command lines
(episodes, faults) with node and parses the JSON they print. Episodes live in
runs/<name>, secrets in runs/<name>.secret, as set by world.runs_dir in the config.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from rlh.config import ROOT, load_config

WORLD_SRC = ROOT / "world" / "src"
NODE_FLAGS = ["--disable-warning=ExperimentalWarning"]

world_app = typer.Typer(help="Create, start, stop and inspect practice-world episodes.",
                        no_args_is_help=True)
console = Console()


class WorldError(RuntimeError):
    pass


def episode_dir(name: str) -> Path:
    return ROOT / load_config()["world"]["runs_dir"] / name


def run_node(script: str, *args: str) -> str:
    node = shutil.which("node")
    if node is None:
        raise WorldError("node not found on PATH")
    cmd = [node, *NODE_FLAGS, str(WORLD_SRC / script), *args]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise WorldError(result.stderr.strip() or f"{script} {' '.join(args)} failed")
    return result.stdout


def run_episode(command: str, directory: Path, *extra: str) -> Any:
    return json.loads(run_node("episode-cli.ts", command, str(directory), *extra))


def inject_fault(directory: Path, fault: str, seed: int = 1) -> Any:
    return json.loads(run_node("fault-cli.ts", "inject", str(directory), fault, "--seed", str(seed)))


def _show(action: Any) -> None:
    try:
        console.print_json(data=action())
    except WorldError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc


def _call(command: str, name: str, *extra: str) -> None:
    _show(lambda: run_episode(command, episode_dir(name), *extra))


@world_app.command(help="Seed a fresh episode folder (wipes any existing one).")
def create(name: str, rows: Annotated[int, typer.Option()] = 2000,
           seed: Annotated[int, typer.Option()] = 1) -> None:
    _call("create", name, "--rows", str(rows), "--seed", str(seed))


@world_app.command(help="Start the API, workers and load generator for an episode.")
def start(name: str, rate: Annotated[int, typer.Option(help="orders per second")] = 20,
          workers: Annotated[int, typer.Option()] = 1) -> None:
    _call("start", name, "--rate", str(rate), "--workers", str(workers))


@world_app.command(help="Kill every process of an episode.")
def stop(name: str) -> None:
    _call("stop", name)


@world_app.command(help="Show process health, queue counts and load counters.")
def status(name: str) -> None:
    _call("status", name)


@world_app.command(help="Break a running episode with a fault template.")
def inject(name: str, fault: str, seed: Annotated[int, typer.Option()] = 1) -> None:
    _show(lambda: inject_fault(episode_dir(name), fault, seed))


@world_app.command(help="List the available fault templates.")
def faults() -> None:
    try:
        console.print(run_node("fault-cli.ts", "list").rstrip() or "no faults registered")
    except WorldError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
