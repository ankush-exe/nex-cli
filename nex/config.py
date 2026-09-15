"""Persistence for the project signals learned by Nex."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from nex.discovery.models import ProjectDiscovery


CONFIG_DIRECTORY = ".nex"
CONFIG_FILENAME = "config.toml"


class ConfigAlreadyExistsError(FileExistsError):
    """Raised when saving would overwrite an existing Nex config."""


@dataclass(frozen=True)
class LearnConfig:
    """The stable, persisted representation of a discovery result."""

    root: Path
    components: tuple[ComponentConfig, ...]


@dataclass(frozen=True)
class ComponentConfig:
    """The serializable representation of one discovered component."""

    name: str
    path: str
    role: str
    signals: tuple[str, ...]
    workflows: tuple[WorkflowConfig, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class WorkflowConfig:
    """The serializable representation of one component workflow."""

    ecosystem: str
    manifest: str
    package_manager: str | None
    scripts: tuple[str, ...]
    metadata: tuple[tuple[str, str], ...]
    suggested_commands: tuple[str, ...]


def build_learn_config(root: Path, discovery: ProjectDiscovery) -> LearnConfig:
    """Convert a project discovery result into Nex's persisted configuration."""
    components = tuple(
        ComponentConfig(
            name=component.name,
            path=component.relative_path.as_posix(),
            role=component.role,
            signals=tuple(signal.name for signal in component.signals),
            workflows=tuple(
                WorkflowConfig(
                    ecosystem=workflow.ecosystem,
                    manifest=workflow.manifest,
                    package_manager=workflow.package_manager,
                    scripts=workflow.scripts,
                    metadata=workflow.metadata,
                    suggested_commands=workflow.suggested_commands,
                )
                for workflow in component.workflows
            ),
            warnings=component.warnings,
        )
        for component in discovery.components
    )
    return LearnConfig(root=root.resolve(), components=components)


def write_learn_config(config: LearnConfig, *, force: bool = False) -> Path:
    """Write a learned config, refusing to replace an existing file by default."""
    config_path = config.root / CONFIG_DIRECTORY / CONFIG_FILENAME
    if config_path.exists() and not force:
        raise ConfigAlreadyExistsError(config_path)

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(render_learn_config(config), encoding="utf-8")
    return config_path


def render_learn_config(config: LearnConfig) -> str:
    """Render the v2 multi-component configuration schema as TOML."""
    lines = [
        "schema_version = 2",
        "",
        "[project]",
        f"name = {_toml_string(config.root.name)}",
        f"root = {_toml_string(str(config.root))}",
    ]
    for component in config.components:
        lines.extend(
            (
                "",
                "[[components]]",
                f"name = {_toml_string(component.name)}",
                f"path = {_toml_string(component.path)}",
                f"role = {_toml_string(component.role)}",
                f"signals = {_toml_string_array(component.signals)}",
            )
        )
        for workflow in component.workflows:
            lines.extend(
                (
                    "",
                    "[[components.workflows]]",
                    f"ecosystem = {_toml_string(workflow.ecosystem)}",
                    f"manifest = {_toml_string(workflow.manifest)}",
                )
            )
            if workflow.package_manager is not None:
                lines.append(
                    f"package_manager = {_toml_string(workflow.package_manager)}"
                )
            lines.append(f"scripts = {_toml_string_array(workflow.scripts)}")
            lines.append(
                f"suggested_commands = {_toml_string_array(workflow.suggested_commands)}"
            )
            if workflow.metadata:
                lines.append("[components.workflows.metadata]")
                for key, value in workflow.metadata:
                    lines.append(f"{_toml_key(key)} = {_toml_string(value)}")
        if component.warnings:
            lines.append(f"warnings = {_toml_string_array(component.warnings)}")

    lines.append("")
    return "\n".join(lines)


def _toml_string(value: str) -> str:
    """Encode a string using TOML's JSON-compatible basic-string syntax."""
    return json.dumps(value)


def _toml_string_array(values: tuple[str, ...]) -> str:
    return f"[{', '.join(_toml_string(value) for value in values)}]"


def _toml_key(value: str) -> str:
    return value if value.replace("-", "").replace("_", "").isalnum() else _toml_string(value)
