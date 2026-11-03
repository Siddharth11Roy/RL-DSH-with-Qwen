"""Command-line entry point for the `rlh` agent.

Ships `version`, `doctor`, `config`, `grade` and the `world` group for
episodes and faults. Baselines, training and evaluation join as later phases
land, so this file stays a thin layer that only parses arguments and prints.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from rlh import __version__
from rlh.config import ConfigError, load_config
from rlh.doctor import run_checks
from rlh.graders import grade as grade_episode
from rlh.world import episode_dir, world_app

app = typer.Typer(help="A terminal agent whose tool-calling policy is trained with RL.",
                  no_args_is_help=True, add_completion=False)
app.add_typer(world_app, name="world")
console = Console()


@app.command(help="Print the rlh version.")
def version() -> None:
    console.print(f"rlh {__version__}")


@app.command(help="Check that this machine can build, run and train the agent.")
def doctor() -> None:
    results = run_checks()
    table = Table(show_header=True, header_style="bold")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")
    for check in results:
        if check.ok:
            status = "[green]ok[/green]"
        elif check.required:
            status = "[red]missing[/red]"
        else:
            status = "[yellow]later[/yellow]"
        table.add_row(check.name, status, check.detail)
    console.print(table)
    blocking = [c for c in results if c.required and not c.ok]
    raise typer.Exit(1 if blocking else 0)


@app.command(help="Score an episode with the grader for its injected fault.")
def grade(name: str) -> None:
    result = grade_episode(episode_dir(name))
    table = Table(title=f"{result.fault}: reward {result.reward:+.2f}", show_header=True)
    for column in ("Check", "Kind", "Result", "Detail"):
        table.add_column(column)
    for check in result.checks:
        mark = "[green]pass[/green]" if check.passed else "[red]fail[/red]"
        table.add_row(check.name, check.kind, mark, check.detail)
    console.print(table)


@app.command(help="Show the settings rlh will use, after merging any override file.")
def config(
    override: Annotated[
        Path | None, typer.Option("--config", "-c", help="YAML file with overrides.")
    ] = None,
) -> None:
    try:
        console.print_json(data=load_config(override))
    except ConfigError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc


if __name__ == "__main__":
    app()
