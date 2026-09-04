"""Command-line entry point for Nex."""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from nex import __version__
from nex.config import ConfigAlreadyExistsError, build_learn_config, write_learn_config
from nex.detection import detect_project


def version_callback(value: bool) -> None:
    """Print the installed Nex CLI version and exit."""
    if value:
        typer.echo(f"nex {__version__}")
        raise typer.Exit()


app = typer.Typer(
    add_completion=False,
    no_args_is_help=False,
    invoke_without_command=True,
    help="Command-line interface for Nex.",
)


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show the Nex version and exit.",
    ),
) -> None:
    """Nex command-line interface."""
    if ctx.invoked_subcommand is None and not version:
        typer.echo(ctx.get_help())


@app.command()
def learn(
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite an existing .nex/config.toml file.",
    ),
) -> None:
    """Detect project signals and save them to .nex/config.toml."""
    root = Path.cwd().resolve()
    detection = detect_project(directory=root)
    console = Console()

    if not detection.found_anything:
        console.print(
            Panel("No supported project signals found in this directory.", title="Nex learn")
        )
    else:
        table = Table(title="Nex learn", show_header=True)
        table.add_column("Type", style="bold")
        table.add_column("Detected")

        if detection.frontend:
            scripts = ", ".join(detection.frontend.scripts) or "no dev/start script"
            table.add_row("Frontend", f"package.json ({scripts})")
        if detection.python_files:
            table.add_row("Python backend", ", ".join(detection.python_files))
        if detection.docker_compose:
            table.add_row("Services", "docker-compose.yml")

        console.print(table)

    try:
        config_path = write_learn_config(
            build_learn_config(root, detection), force=force
        )
    except ConfigAlreadyExistsError as error:
        console.print(
            f"[yellow]Nex config already exists at {error.filename}. "
            "Use --force to overwrite it.[/yellow]"
        )
        raise typer.Exit(code=1) from None

    console.print(f"[green]Saved Nex config to {config_path}[/green]")


def run() -> None:
    """Run the Nex CLI."""
    app()
