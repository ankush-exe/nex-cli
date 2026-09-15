import json

from typer.testing import CliRunner

from nex.cli import app


runner = CliRunner()


def test_help() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Usage:" in result.output


def test_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.output == "nex 0.3.1\n"


def test_no_arguments_requires_config(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app)

    assert result.exit_code == 1
    assert "Run `nex learn` first" in result.output


def test_learn_reports_detected_project_signals(tmp_path, monkeypatch) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"dev": "vite"}}), encoding="utf-8"
    )
    (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["learn"])

    assert result.exit_code == 0
    assert "package.json" in result.output
    assert "javascript" in result.output
    assert "python" in result.output
    assert "dev" in result.output
    assert "Saved Nex config to" in result.output
    assert (tmp_path / ".nex" / "config.toml").is_file()


def test_learn_discovers_nested_components_and_warnings(tmp_path, monkeypatch) -> None:
    client = tmp_path / "client"
    server = tmp_path / "server"
    client.mkdir()
    server.mkdir()
    (client / "package.json").write_text('{"scripts": {"dev": "vite"}}', encoding="utf-8")
    (server / "package.json").write_text("{", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["learn"])

    assert result.exit_code == 0
    assert "client" in result.output
    assert "server" in result.output
    assert "Warning:" in result.output


def test_learn_refuses_to_overwrite_existing_config(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / ".nex" / "config.toml"
    config_path.parent.mkdir()
    config_path.write_text("keep = true\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["learn"])

    assert result.exit_code == 1
    assert "Use --force to overwrite it." in result.output
    assert config_path.read_text(encoding="utf-8") == "keep = true\n"


def test_learn_force_overwrites_existing_config(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / ".nex" / "config.toml"
    config_path.parent.mkdir()
    config_path.write_text("old = true\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["learn", "--force"])

    assert result.exit_code == 0
    assert "Saved Nex config to" in result.output
    assert "old = true" not in config_path.read_text(encoding="utf-8")
