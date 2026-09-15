"""Domain models for project discovery."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Signal:
    """A recognized project or service manifest."""

    name: str
    ecosystem: str
    valid: bool = True
    warning: str | None = None


@dataclass(frozen=True)
class Workflow:
    """Deterministic workflow information extracted from a component."""

    ecosystem: str
    manifest: str
    package_manager: str | None = None
    scripts: tuple[str, ...] = ()
    metadata: tuple[tuple[str, str], ...] = ()
    suggested_commands: tuple[str, ...] = ()


@dataclass(frozen=True)
class Component:
    """A directory containing at least one recognized project signal."""

    name: str
    relative_path: Path
    role: str
    signals: tuple[Signal, ...]
    workflows: tuple[Workflow, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProjectDiscovery:
    """The complete bounded discovery result for a project root."""

    root: Path
    components: tuple[Component, ...]
    warnings: tuple[str, ...] = ()

    @property
    def found_anything(self) -> bool:
        """Whether at least one component was found."""
        return bool(self.components)