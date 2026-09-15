"""Bounded filesystem traversal for project discovery."""

from __future__ import annotations

from pathlib import Path

from nex.discovery.detectors import detect_component
from nex.discovery.models import Component, ProjectDiscovery


DEFAULT_MAX_DEPTH = 3
IGNORED_DIRECTORIES = frozenset(
    {
        ".git",
        ".nex",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "vendor",
        "dist",
        "build",
        "target",
        ".cache",
        ".pytest_cache",
        "__pycache__",
        ".tox",
        ".mypy_cache",
        ".ruff_cache",
        "coverage",
    }
)


def discover_project(root: Path, *, max_depth: int = DEFAULT_MAX_DEPTH) -> ProjectDiscovery:
    """Discover recognized components below *root* to a bounded depth."""
    resolved_root = root.resolve()
    components: list[Component] = []

    for directory, depth in _walk_directories(resolved_root, max_depth=max_depth):
        component = detect_component(resolved_root, directory)
        if component is not None:
            components.append(component)

    return ProjectDiscovery(root=resolved_root, components=tuple(components))


def _walk_directories(root: Path, *, max_depth: int):
    """Yield directories in deterministic order without following symlinks."""
    if max_depth < 0:
        return

    stack = [(root, 0)]
    while stack:
        directory, depth = stack.pop()
        yield directory, depth
        if depth >= max_depth:
            continue

        children = []
        try:
            entries = sorted(directory.iterdir(), key=lambda path: path.name)
        except OSError:
            continue
        for entry in entries:
            if entry.name in IGNORED_DIRECTORIES or not entry.is_dir() or entry.is_symlink():
                continue
            children.append((entry, depth + 1))
        stack.extend(reversed(children))