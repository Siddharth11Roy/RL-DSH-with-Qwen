"""Command-line entry point for the `rlh` agent.

Phase 0 ships `version`, `doctor` and `config`. Episodes, baselines, training
and evaluation become subcommands here as later phases land, so this file
stays a thin layer that only parses arguments and prints results.
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

app = typer.Typer(help="A terminal agent whose tool-calling policy is trained with RL.",
                  no_args_is_help=True, add_completion=False)
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
