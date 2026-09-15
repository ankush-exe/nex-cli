import json
import os

import pytest

from nex.discovery import DEFAULT_MAX_DEPTH, discover_project


def test_discovers_root_package_json_and_lockfile_workflow(tmp_path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"dev": "vite", "start": "vite preview"}}),
        encoding="utf-8",
    )
    (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: 9\n", encoding="utf-8")

    discovery = discover_project(tmp_path)

    assert len(discovery.components) == 1
    component = discovery.components[0]
    assert component.name == tmp_path.name
    assert component.relative_path.parts == ()
    assert component.role == "unknown"
    workflow = component.workflows[0]
    assert workflow.package_manager == "pnpm"
    assert workflow.scripts == ("dev", "start")
    assert workflow.suggested_commands == ("pnpm run dev", "pnpm run start")


def test_discovers_root_python_project_and_metadata(tmp_path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'example-api'\nrequires-python = '>=3.12'\n",
        encoding="utf-8",
    )
    (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")

    component = discover_project(tmp_path).components[0]

    assert [signal.name for signal in component.signals] == [
        "pyproject.toml",
        "requirements.txt",
    ]
    assert component.workflows[0].metadata == (
        ("name", "example-api"),
        ("requires-python", ">=3.12"),
    )


def test_discovers_root_docker_compose(tmp_path) -> None:
    (tmp_path / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")

    component = discover_project(tmp_path).components[0]

    assert component.role == "service"
    assert component.signals[0].ecosystem == "docker"
    assert component.workflows[0].suggested_commands == ("docker compose up",)


def test_discovers_client_and_server_without_name_based_roles(tmp_path) -> None:
    client = tmp_path / "client"
    server = tmp_path / "server"
    client.mkdir()
    server.mkdir()
    (client / "package.json").write_text("{}", encoding="utf-8")
    (server / "requirements.txt").write_text("fastapi\n", encoding="utf-8")

    components = discover_project(tmp_path).components

    assert [(item.name, item.relative_path.as_posix()) for item in components] == [
        ("client", "client"),
        ("server", "server"),
    ]
    assert {item.role for item in components} == {"unknown"}


def test_discovers_nested_components_to_default_depth(tmp_path) -> None:
    nested = tmp_path / "one" / "two" / "three"
    nested.mkdir(parents=True)
    (nested / "requirements.txt").write_text("httpx\n", encoding="utf-8")

    components = discover_project(tmp_path).components

    assert len(components) == 1
    assert components[0].relative_path.as_posix() == "one/two/three"
    assert DEFAULT_MAX_DEPTH == 3


def test_does_not_discover_beyond_depth_limit(tmp_path) -> None:
    too_deep = tmp_path / "one" / "two" / "three" / "four"
    too_deep.mkdir(parents=True)
    (too_deep / "requirements.txt").write_text("httpx\n", encoding="utf-8")

    assert discover_project(tmp_path).components == ()


@pytest.mark.parametrize(
    "directory_name",
    [
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
    ],
)
def test_ignores_generated_and_environment_directories(tmp_path, directory_name) -> None:
    ignored = tmp_path / directory_name
    ignored.mkdir()
    (ignored / "package.json").write_text("{}", encoding="utf-8")

    assert discover_project(tmp_path).components == ()


def test_preserves_malformed_package_json_as_warning(tmp_path) -> None:
    (tmp_path / "package.json").write_text("{", encoding="utf-8")

    component = discover_project(tmp_path).components[0]

    assert component.signals[0].valid is False
    assert component.signals[0].warning is not None
    assert component.warnings
    assert component.workflows[0].scripts == ()


def test_empty_project_has_no_components(tmp_path) -> None:
    discovery = discover_project(tmp_path)

    assert not discovery.found_anything
    assert discovery.components == ()


def test_component_order_is_deterministic(tmp_path) -> None:
    for name in ("zulu", "alpha", "middle"):
        directory = tmp_path / name
        directory.mkdir()
        (directory / "requirements.txt").write_text("httpx\n", encoding="utf-8")

    first = discover_project(tmp_path)
    second = discover_project(tmp_path)

    assert [item.relative_path.as_posix() for item in first.components] == [
        "alpha",
        "middle",
        "zulu",
    ]
    assert first == second


def test_does_not_follow_symlinked_directories(tmp_path) -> None:
    real_directory = tmp_path / "real"
    real_directory.mkdir()
    (real_directory / "requirements.txt").write_text("httpx\n", encoding="utf-8")
    link = tmp_path / "linked"
    try:
        os.symlink(real_directory, link, target_is_directory=True)
    except OSError:
        pytest.skip("symbolic links are unavailable")

    components = discover_project(tmp_path).components

    assert [item.relative_path.as_posix() for item in components] == ["real"]


def test_unknown_package_manager_is_explicit(tmp_path) -> None:
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")

    workflow = discover_project(tmp_path).components[0].workflows[0]

    assert workflow.package_manager is None