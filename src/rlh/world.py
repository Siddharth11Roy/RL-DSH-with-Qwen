"""Python bridge to the practice world, exposed as `rlh world ...`.

The world itself is TypeScript; this module only calls its episode command line
with node and parses the JSON it prints. Episodes live in runs/<name>, with the
hidden checksum in runs/<name>.secret, as set by world.runs_dir in the config.
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

EPISODE_CLI = ROOT / "world" / "src" / "episode-cli.ts"
NODE_FLAGS = ["--disable-warning=ExperimentalWarning"]

world_app = typer.Typer(help="Create, start, stop and inspect practice-world episodes.",
                        no_args_is_help=True)
console = Console()


class WorldError(RuntimeError):
    pass


def episode_dir(name: str) -> Path:
    return ROOT / load_config()["world"]["runs_dir"] / name


def run_episode(command: str, directory: Path, *extra: str) -> Any:
    node = shutil.which("node")
    if node is None:
        raise WorldError("node not found on PATH")
    args = [node, *NODE_FLAGS, str(EPISODE_CLI), command, str(directory), *extra]
    result = subprocess.run(args, check=False, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise WorldError(result.stderr.strip() or f"episode {command} failed")
    return json.loads(result.stdout)


def _call(command: str, name: str, *extra: str) -> None:
    try:
        console.print_json(data=run_episode(command, episode_dir(name), *extra))
    except WorldError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc


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
