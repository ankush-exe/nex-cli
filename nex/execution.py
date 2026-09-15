"""Execution of one workflow selected from a saved Nex config."""

from __future__ import annotations

import shlex
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path

from nex.config import CONFIG_DIRECTORY, CONFIG_FILENAME


@dataclass(frozen=True)
class ExecutionTarget:
    """One command and working directory that Nex can execute."""

    component_path: str
    command: tuple[str, ...]
    cwd: Path


class WorkflowConfigError(ValueError):
    """Raised when a saved config cannot identify a runnable workflow."""


def run_configured_workflow(root: Path, component: str | None = None) -> int:
    """Run one configured workflow and return its process exit code."""
    root = root.resolve()
    config_path = root / CONFIG_DIRECTORY / CONFIG_FILENAME
    if not config_path.is_file():
        raise WorkflowConfigError(
            "No Nex config found. Run `nex learn` first, then run `nex` again."
        )

    targets = _read_targets(config_path, root)
    if component is not None:
        normalized_component = _normalize_component_path(component, root)
        targets = tuple(
            target for target in targets if target.component_path == normalized_component
        )
        if not targets:
            raise WorkflowConfigError(
                f"No runnable workflow found for component '{component}'."
            )
    elif len(targets) > 1:
        choices = ", ".join(target.component_path for target in targets)
        raise WorkflowConfigError(
            f"Multiple runnable components found ({choices}). "
            "Choose one with `nex --component <path>`."
        )

    if not targets:
        raise WorkflowConfigError(
            "No runnable workflow found in the Nex config. Run `nex learn --force` "
            "after adding a supported dev or start script."
        )

    return _run_process(targets[0])


def _read_targets(config_path: Path, root: Path) -> tuple[ExecutionTarget, ...]:
    try:
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise WorkflowConfigError(f"Could not read Nex config: {error}") from None

    schema_version = data.get("schema_version")
    if schema_version == 1:
        return _read_v1_targets(data, root)
    if schema_version == 2:
        return _read_v2_targets(data, root)
    raise WorkflowConfigError(
        f"Unsupported Nex config schema version: {schema_version!r}. "
        "Run `nex learn --force` to regenerate it."
    )


def _read_v1_targets(data: dict, root: Path) -> tuple[ExecutionTarget, ...]:
    frontend = data.get("frontend")
    if not isinstance(frontend, dict) or not frontend.get("detected"):
        return ()
    command = frontend.get("command")
    if not isinstance(command, str) or not command.strip():
        return ()
    return (ExecutionTarget(".", _parse_command(command), root),)


def _read_v2_targets(data: dict, root: Path) -> tuple[ExecutionTarget, ...]:
    components = data.get("components", [])
    if not isinstance(components, list):
        raise WorkflowConfigError("Nex config has an invalid components section.")

    targets: list[ExecutionTarget] = []
    normalized_paths: set[str] = set()
    for component in components:
        if not isinstance(component, dict):
            continue
        component_path = component.get("path")
        workflows = component.get("workflows", [])
        if not isinstance(component_path, str) or not isinstance(workflows, list):
            continue
        normalized_path, component_directory = _validated_component_path(component_path, root)
        if normalized_path in normalized_paths:
            raise WorkflowConfigError(
                f"Nex config has duplicate component path '{normalized_path}'."
            )
        normalized_paths.add(normalized_path)
        target: ExecutionTarget | None = None
        for workflow in workflows:
            if not isinstance(workflow, dict):
                continue
            commands = workflow.get("suggested_commands", [])
            if not isinstance(commands, list):
                continue
            for command in commands:
                if not isinstance(command, str) or not command.strip():
                    continue
                target = ExecutionTarget(
                    normalized_path,
                    _parse_command(command),
                    component_directory,
                )
                break
            if target is not None:
                break
        if target is not None:
            targets.append(target)
    return tuple(targets)


def _normalize_component_path(component_path: str, root: Path) -> str:
    """Return a safe, normalized component path relative to *root*."""
    return _validated_component_path(component_path, root)[0]


def _validated_component_path(component_path: str, root: Path) -> tuple[str, Path]:
    """Validate a persisted component path and return its normalized location."""
    candidate = Path(component_path)
    if candidate.is_absolute():
        raise WorkflowConfigError(
            f"Invalid component path '{component_path}': absolute paths are not allowed."
        )

    resolved_root = root.resolve()
    resolved_candidate = (resolved_root / candidate).resolve(strict=False)
    try:
        relative_path = resolved_candidate.relative_to(resolved_root)
    except ValueError:
        raise WorkflowConfigError(
            f"Invalid component path '{component_path}': path is outside the project root."
        ) from None

    normalized_path = relative_path.as_posix() if relative_path.parts else "."
    return normalized_path, resolved_candidate


def _parse_command(command: str) -> tuple[str, ...]:
    """Parse one saved command without enabling shell interpretation."""
    try:
        parsed = tuple(shlex.split(command))
    except ValueError as error:
        raise WorkflowConfigError(f"Invalid workflow command: {error}") from None
    if not parsed:
        raise WorkflowConfigError("Invalid workflow command: command is empty.")
    return parsed


def _run_process(target: ExecutionTarget) -> int:
    try:
        process = subprocess.Popen(target.command, cwd=target.cwd)
    except (OSError, ValueError) as error:
        command = shlex.join(target.command)
        raise WorkflowConfigError(
            f"Could not start workflow `{command}` in {target.cwd}: {error}"
        ) from None
    try:
        returncode = process.wait()
    except KeyboardInterrupt:
        try:
            process.terminate()
        except ProcessLookupError:
            return 130
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except ProcessLookupError:
                return 130
            try:
                process.wait()
            except ProcessLookupError:
                pass
        return 130
    return 130 if returncode == -2 else returncode
