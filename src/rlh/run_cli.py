"""The `rlh run` command: one incident, start to finish, printed as it ended.

Picks a backend (an OpenAI-compatible model, or a scripted list of moves from a
JSON file), runs the incident through runner.run_incident and prints each step
and the graded checks, so a human can see exactly what the agent did and why.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from rlh.agent.backends import Backend, OpenAIBackend, ScriptedBackend
from rlh.config import load_config
from rlh.runner import load_script, run_incident

console = Console()


def show(traj) -> None:
    steps = Table(title=f"{traj.task['fault']} (seed {traj.task['seed']}) with {traj.model}")
    for column in ("Turn", "Tool", "Arguments", "Output"):
        steps.add_column(column, overflow="fold")
    for step in traj.steps:
        output = (step.error and f"[red]{step.error}[/red]") or step.output[:160]
        steps.add_row(str(step.turn), step.tool or "-", str(step.arguments or "")[:80], output)
    console.print(steps)
    console.print(f"ended: {traj.ended}   summary: {traj.summary or '-'}")
    for check in traj.grade["checks"]:
        mark = "[green]pass[/green]" if check["passed"] else "[red]fail[/red]"
        console.print(f"  {mark} {check['kind']:<6} {check['name']}  {check['detail']}")
    console.print(f"[bold]reward {traj.reward:+.2f}[/bold]")


def run(
    fault: str,
    seed: Annotated[int, typer.Option()] = 1,
    model: Annotated[str | None, typer.Option(help="model name on the server")] = None,
    base_url: Annotated[str | None, typer.Option(help="OpenAI-compatible base URL")] = None,
    api_key_env: Annotated[str, typer.Option(help="env var holding the API key")] = "RLH_API_KEY",
    scripted: Annotated[Path | None, typer.Option(help="JSON file of moves instead of a model")] = None,
    max_turns: Annotated[int | None, typer.Option()] = None,
) -> None:
    config = load_config()
    if max_turns:
        config["harness"]["max_turns"] = max_turns
    backend: Backend
    if scripted:
        backend = ScriptedBackend(load_script(scripted), name=f"scripted:{scripted.stem}")
    else:
        endpoint = config["endpoint"]
        backend = OpenAIBackend(model or endpoint["model_name"], base_url or endpoint["base_url"],
                                api_key_env)
    show(run_incident(backend, fault, seed, config))
