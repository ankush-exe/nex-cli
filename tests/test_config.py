import json
import tomllib

import pytest

from nex.config import (
    ConfigAlreadyExistsError,
    build_learn_config,
    write_learn_config,
)
from nex.detection import detect_project


def test_writes_config_for_a_fresh_project_directory(tmp_path) -> None:
    (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    config = build_learn_config(tmp_path, detect_project(tmp_path))

    config_path = write_learn_config(config)

    assert config_path == tmp_path / ".nex" / "config.toml"
    assert config_path.is_file()


def test_does_not_clobber_an_existing_config(tmp_path) -> None:
    config_path = tmp_path / ".nex" / "config.toml"
    config_path.parent.mkdir()
    config_path.write_text("keep = true\n", encoding="utf-8")
    config = build_learn_config(tmp_path, detect_project(tmp_path))

    with pytest.raises(ConfigAlreadyExistsError):
        write_learn_config(config)

    assert config_path.read_text(encoding="utf-8") == "keep = true\n"


def test_force_overwrites_an_existing_config(tmp_path) -> None:
    config_path = tmp_path / ".nex" / "config.toml"
    config_path.parent.mkdir()
    config_path.write_text("old = true\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    config = build_learn_config(tmp_path, detect_project(tmp_path))

    write_learn_config(config, force=True)

    assert "old = true" not in config_path.read_text(encoding="utf-8")
    assert tomllib.loads(config_path.read_text(encoding="utf-8"))["backend"] == {
        "signals": ["requirements.txt"]
    }


def test_config_content_captures_a_mixed_project(tmp_path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"start": "next start"}}), encoding="utf-8"
    )
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'api'\n", encoding="utf-8")
    (tmp_path / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")

    config_path = write_learn_config(
        build_learn_config(tmp_path, detect_project(tmp_path))
    )
    content = tomllib.loads(config_path.read_text(encoding="utf-8"))

    assert content == {
        "schema_version": 1,
        "project": {"name": tmp_path.name, "root": str(tmp_path.resolve())},
        "frontend": {
            "detected": True,
            "script": "start",
            "command": "npm run start",
        },
        "backend": {"signals": ["pyproject.toml"]},
        "services": {"docker_compose": True},
    }
