"""Multi-directory project discovery for Nex."""

from nex.discovery.models import Component, ProjectDiscovery, Signal, Workflow
from nex.discovery.scanner import DEFAULT_MAX_DEPTH, discover_project

__all__ = [
    "Component",
    "DEFAULT_MAX_DEPTH",
    "ProjectDiscovery",
    "Signal",
    "Workflow",
    "discover_project",
]