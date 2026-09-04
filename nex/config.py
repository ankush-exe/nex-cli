"""Persistence for the project signals learned by Nex."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from nex.detection import ProjectDetection


CONFIG_DIRECTORY = ".nex"
CONFIG_FILENAME = "config.toml"


class ConfigAlreadyExistsError(FileExistsError):
    """Raised when saving would overwrite an existing Nex config."""


@dataclass(frozen=True)
class LearnConfig:
    """The stable, persisted representation of a detection result."""

    root: Path
    frontend_script: str | None
    backend_signals: tuple[str, ...]
    docker_compose: bool


def build_learn_config(root: Path, detection: ProjectDetection) -> LearnConfig:
    """Convert a project detection result into Nex's persisted configuration."""
    frontend_script = None
    if detection.frontend and detection.frontend.scripts:
        frontend_script = detection.frontend.scripts[0]

    return LearnConfig(
        root=root.resolve(),
        frontend_script=frontend_script,
        backend_signals=detection.python_files,
        docker_compose=detection.docker_compose,
    )


def write_learn_config(config: LearnConfig, *, force: bool = False) -> Path:
    """Write a learned config, refusing to replace an existing file by default."""
    config_path = config.root / CONFIG_DIRECTORY / CONFIG_FILENAME
    if config_path.exists() and not force:
        raise ConfigAlreadyExistsError(config_path)

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(render_learn_config(config), encoding="utf-8")
    return config_path


def render_learn_config(config: LearnConfig) -> str:
    """Render the fixed v1 configuration schema as TOML."""
    lines = [
        "schema_version = 1",
        "",
        "[project]",
        f"name = {_toml_string(config.root.name)}",
        f"root = {_toml_string(str(config.root))}",
        "",
        "[frontend]",
        f"detected = {'true' if config.frontend_script is not None else 'false'}",
    ]
    if config.frontend_script is not None:
        lines.extend(
            (
                f"script = {_toml_string(config.frontend_script)}",
                f"command = {_toml_string(f'npm run {config.frontend_script}')}",
            )
        )

    lines.extend(
        (
            "",
            "[backend]",
            f"signals = {_toml_string_array(config.backend_signals)}",
            "",
            "[services]",
            f"docker_compose = {'true' if config.docker_compose else 'false'}",
            "",
        )
    )
    return "\n".join(lines)


def _toml_string(value: str) -> str:
    """Encode a string using TOML's JSON-compatible basic-string syntax."""
    return json.dumps(value)


def _toml_string_array(values: tuple[str, ...]) -> str:
    return f"[{', '.join(_toml_string(value) for value in values)}]"
