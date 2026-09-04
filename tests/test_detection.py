import json

from nex.detection import detect_project


def test_detects_frontend_project_and_known_scripts(tmp_path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"dev": "vite", "test": "vitest"}}), encoding="utf-8"
    )

    detection = detect_project(tmp_path)

    assert detection.frontend is not None
    assert detection.frontend.scripts == ("dev",)
    assert detection.python_files == ()
    assert not detection.docker_compose


def test_detects_python_backend_project(tmp_path) -> None:
    (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")

    detection = detect_project(tmp_path)

    assert detection.frontend is None
    assert detection.python_files == ("requirements.txt",)
    assert not detection.docker_compose


def test_detects_mixed_project(tmp_path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"start": "next start"}}), encoding="utf-8"
    )
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'api'\n", encoding="utf-8")
    (tmp_path / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")

    detection = detect_project(tmp_path)

    assert detection.frontend is not None
    assert detection.frontend.scripts == ("start",)
    assert detection.python_files == ("pyproject.toml",)
    assert detection.docker_compose


def test_reports_no_signals_for_empty_directory(tmp_path) -> None:
    detection = detect_project(tmp_path)

    assert not detection.found_anything
