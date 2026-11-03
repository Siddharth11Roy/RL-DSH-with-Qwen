"""Command-line entry point for the `rlh` agent.

Phase 0 ships `version` and `doctor`. Running episodes, baselines, training
and evaluation become subcommands here as later phases land, so this file
stays a thin layer that only parses arguments and prints results.
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from rlh import __version__
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


if __name__ == "__main__":
    app()
