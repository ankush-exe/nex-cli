"""Command-line entry point for Nex."""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from nex import __version__
from nex.config import ConfigAlreadyExistsError, build_learn_config, write_learn_config
from nex.discovery import discover_project
from nex.execution import WorkflowConfigError, run_configured_workflow


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
    component: str | None = typer.Option(
        None,
        "--component",
        help="Select one component name or path instead of running all workflows.",
    ),
) -> None:
    """Nex command-line interface."""
    if ctx.invoked_subcommand is None and not version:
        try:
            exit_code = run_configured_workflow(Path.cwd().resolve(), component)
        except WorkflowConfigError as error:
            typer.echo(str(error), err=True)
            raise typer.Exit(code=1) from None
        raise typer.Exit(code=exit_code)


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
    discovery = discover_project(root)
    console = Console()

    if not discovery.found_anything:
        console.print(
            Panel("No supported project signals found in this directory.", title="Nex learn")
        )
    else:
        table = Table(title="Nex learn", show_header=True)
        table.add_column("Component", style="bold")
        table.add_column("Role")
        table.add_column("Signals")
        table.add_column("Workflow")

        for component in discovery.components:
            workflows = []
            for workflow in component.workflows:
                details = workflow.ecosystem
                if workflow.package_manager:
                    details += f"/{workflow.package_manager}"
                if workflow.scripts:
                    details += f" ({', '.join(workflow.scripts)})"
                workflows.append(details)
            table.add_row(
                component.relative_path.as_posix(),
                component.role,
                ", ".join(signal.name for signal in component.signals),
                ", ".join(workflows) or "-",
            )

        console.print(table)
        for component in discovery.components:
            for warning in component.warnings:
                console.print(f"[yellow]Warning: {warning}[/yellow]")

    try:
        config_path = write_learn_config(
            build_learn_config(root, discovery), force=force
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
