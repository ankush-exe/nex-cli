"""Manifest detectors used by the discovery scanner."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from nex.discovery.models import Component, Signal, Workflow


SIGNAL_FILENAMES = (
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "docker-compose.yml",
)

_PACKAGE_MANAGER_LOCKFILES = (
    ("pnpm-lock.yaml", "pnpm"),
    ("yarn.lock", "yarn"),
    ("bun.lock", "bun"),
    ("bun.lockb", "bun"),
    ("package-lock.json", "npm"),
)


def detect_component(root: Path, directory: Path) -> Component | None:
    """Build a component from recognized files in *directory*, if any exist."""
    present = {filename for filename in SIGNAL_FILENAMES if (directory / filename).is_file()}
    if not present:
        return None

    signals: list[Signal] = []
    workflows: list[Workflow] = []
    warnings: list[str] = []

    if "package.json" in present:
        signal, workflow, warning = _detect_package(directory)
        signals.append(signal)
        if workflow is not None:
            workflows.append(workflow)
        if warning is not None:
            warnings.append(warning)

    if "pyproject.toml" in present:
        signal, workflow, warning = _detect_pyproject(directory)
        signals.append(signal)
        if workflow is not None:
            workflows.append(workflow)
        if warning is not None:
            warnings.append(warning)

    if "requirements.txt" in present:
        signals.append(Signal(name="requirements.txt", ecosystem="python"))
        workflows.append(
            Workflow(ecosystem="python", manifest="requirements.txt")
        )

    if "docker-compose.yml" in present:
        signals.append(Signal(name="docker-compose.yml", ecosystem="docker"))
        workflows.append(
            Workflow(
                ecosystem="docker",
                manifest="docker-compose.yml",
                suggested_commands=("docker compose up",),
            )
        )

    relative_path = directory.relative_to(root)
    return Component(
        name=root.name if not relative_path.parts else directory.name,
        relative_path=relative_path if relative_path.parts else Path("."),
        role="service" if "docker-compose.yml" in present else "unknown",
        signals=tuple(signals),
        workflows=tuple(workflows),
        warnings=tuple(warnings),
    )


def _detect_package(
    directory: Path,
) -> tuple[Signal, Workflow | None, str | None]:
    package_path = directory / "package.json"
    package_manager = _detect_package_manager(directory)
    try:
        package_data = json.loads(package_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        warning = f"Could not parse {package_path.name}: {error}"
        return (
            Signal("package.json", "javascript", valid=False, warning=warning),
            Workflow(
                ecosystem="javascript",
                manifest="package.json",
                package_manager=package_manager,
            ),
            warning,
        )

    if not isinstance(package_data, dict):
        warning = "Could not parse package.json: top-level value is not an object"
        return (
            Signal("package.json", "javascript", valid=False, warning=warning),
            Workflow(
                ecosystem="javascript",
                manifest="package.json",
                package_manager=package_manager,
            ),
            warning,
        )

    scripts_data = package_data.get("scripts", {})
    scripts = tuple(
        name for name in ("dev", "start") if isinstance(scripts_data, dict) and name in scripts_data
    )
    suggested_commands = tuple(f"{package_manager or 'npm'} run {script}" for script in scripts)
    return (
        Signal("package.json", "javascript"),
        Workflow(
            ecosystem="javascript",
            manifest="package.json",
            package_manager=package_manager,
            scripts=scripts,
            suggested_commands=suggested_commands,
        ),
        None,
    )


def _detect_pyproject(
    directory: Path,
) -> tuple[Signal, Workflow | None, str | None]:
    pyproject_path = directory / "pyproject.toml"
    try:
        project_data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        warning = f"Could not parse {pyproject_path.name}: {error}"
        return Signal("pyproject.toml", "python", valid=False, warning=warning), None, warning

    metadata: list[tuple[str, str]] = []
    project = project_data.get("project")
    if isinstance(project, dict):
        for key in ("name", "requires-python"):
            value = project.get(key)
            if isinstance(value, str):
                metadata.append((key, value))

    return (
        Signal("pyproject.toml", "python"),
        Workflow(
            ecosystem="python",
            manifest="pyproject.toml",
            metadata=tuple(metadata),
        ),
        None,
    )


def _detect_package_manager(directory: Path) -> str | None:
    for filename, package_manager in _PACKAGE_MANAGER_LOCKFILES:
        if (directory / filename).is_file():
            return package_manager
    return None