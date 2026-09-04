"""Read-only project signal detection for Nex."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FrontendDetection:
    """A JavaScript project and the conventional start scripts it exposes."""

    scripts: tuple[str, ...]


@dataclass(frozen=True)
class ProjectDetection:
    """Common project signals found in a directory."""

    frontend: FrontendDetection | None
    python_files: tuple[str, ...]
    docker_compose: bool

    @property
    def found_anything(self) -> bool:
        """Whether any supported signal was found."""
        return bool(self.frontend or self.python_files or self.docker_compose)


def detect_project(directory: Path) -> ProjectDetection:
    """Inspect *directory* without modifying it or traversing subdirectories."""
    package_json = directory / "package.json"
    frontend = _detect_frontend(package_json) if package_json.is_file() else None
    python_files = tuple(
        filename
        for filename in ("requirements.txt", "pyproject.toml")
        if (directory / filename).is_file()
    )

    return ProjectDetection(
        frontend=frontend,
        python_files=python_files,
        docker_compose=(directory / "docker-compose.yml").is_file(),
    )


def _detect_frontend(package_json: Path) -> FrontendDetection:
    """Read known npm scripts, tolerating malformed package metadata."""
    try:
        package_data = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return FrontendDetection(scripts=())

    scripts = package_data.get("scripts", {})
    if not isinstance(scripts, dict):
        return FrontendDetection(scripts=())

    return FrontendDetection(
        scripts=tuple(name for name in ("dev", "start") if name in scripts),
    )
