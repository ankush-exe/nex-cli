import json
import shlex
import subprocess
import sys
from unittest.mock import Mock, patch

import pytest

from nex.execution import WorkflowConfigError, run_configured_workflow


def write_config(root, content: str) -> None:
    config_path = root / ".nex" / "config.toml"
    config_path.parent.mkdir()
    config_path.write_text(content, encoding="utf-8")


def test_missing_config_is_explicit(tmp_path) -> None:
    with pytest.raises(WorkflowConfigError, match="Run `nex learn` first"):
        run_configured_workflow(tmp_path)


def test_runs_the_single_v2_suggested_command_in_component_directory(tmp_path) -> None:
    component = tmp_path / "client"
    component.mkdir()
    write_config(
        tmp_path,
        """
schema_version = 2

[[components]]
path = "client"

[[components.workflows]]
suggested_commands = ["npm run dev"]
""",
    )
    process = Mock()
    process.wait.return_value = 0

    with patch("nex.execution.subprocess.Popen", return_value=process) as popen:
        result = run_configured_workflow(tmp_path)

    assert result == 0
    popen.assert_called_once_with(("npm", "run", "dev"), cwd=component)
    process.wait.assert_called_once_with()


def test_nonzero_child_exit_code_is_returned(tmp_path) -> None:
    write_config(
        tmp_path,
        """
schema_version = 2

[[components]]
path = "."

[[components.workflows]]
suggested_commands = ["python -m app"]
""",
    )
    process = Mock()
    process.wait.return_value = 23

    with patch("nex.execution.subprocess.Popen", return_value=process):
        assert run_configured_workflow(tmp_path) == 23


def test_single_component_uses_first_suggested_command(tmp_path) -> None:
    write_config(
        tmp_path,
        """
schema_version = 2

[[components]]
path = "."
[[components.workflows]]
suggested_commands = ["npm run dev", "npm run start"]
""",
    )
    process = Mock()
    process.wait.return_value = 0

    with patch("nex.execution.subprocess.Popen", return_value=process) as popen:
        assert run_configured_workflow(tmp_path) == 0

    popen.assert_called_once_with(("npm", "run", "dev"), cwd=tmp_path)


def test_missing_executable_is_a_workflow_error(tmp_path) -> None:
    write_config(
        tmp_path,
        """
schema_version = 2

[[components]]
path = "."
[[components.workflows]]
suggested_commands = ["missing-nex-command"]
""",
    )

    with pytest.raises(WorkflowConfigError, match="Could not start workflow"):
        run_configured_workflow(tmp_path)


def test_multiple_runnable_components_require_selection(tmp_path) -> None:
    write_config(
        tmp_path,
        """
schema_version = 2

[[components]]
path = "client"
[[components.workflows]]
suggested_commands = ["npm run dev"]

[[components]]
path = "admin"
[[components.workflows]]
suggested_commands = ["npm run dev"]
""",
    )

    with pytest.raises(WorkflowConfigError, match="--component"):
        run_configured_workflow(tmp_path)


def test_component_selection_runs_only_requested_workflow(tmp_path) -> None:
    write_config(
        tmp_path,
        """
schema_version = 2

[[components]]
path = "client"
[[components.workflows]]
suggested_commands = ["npm run dev"]

[[components]]
path = "admin"
[[components.workflows]]
suggested_commands = ["npm run start"]
""",
    )
    process = Mock()
    process.wait.return_value = 0

    with patch("nex.execution.subprocess.Popen", return_value=process) as popen:
        result = run_configured_workflow(tmp_path, "admin")

    assert result == 0
    popen.assert_called_once_with(("npm", "run", "start"), cwd=tmp_path / "admin")


@pytest.mark.parametrize("component_path", ["../outside", "client/../../outside"])
def test_component_path_cannot_escape_project_root(tmp_path, component_path) -> None:
    write_config(
        tmp_path,
        f'''schema_version = 2

[[components]]
path = "{component_path}"
[[components.workflows]]
suggested_commands = ["echo run"]
''',
    )

    with pytest.raises(WorkflowConfigError, match="outside the project root"):
        run_configured_workflow(tmp_path)


def test_absolute_component_path_is_rejected(tmp_path) -> None:
    write_config(
        tmp_path,
        f'''schema_version = 2

[[components]]
path = "{tmp_path.as_posix()}"
[[components.workflows]]
suggested_commands = ["echo run"]
''',
    )

    with pytest.raises(WorkflowConfigError, match="absolute paths"):
        run_configured_workflow(tmp_path)


def test_symlink_component_cannot_escape_project_root(tmp_path) -> None:
    outside = tmp_path.parent / "nex-outside-component"
    outside.mkdir()
    (tmp_path / "escape").symlink_to(outside, target_is_directory=True)
    write_config(
        tmp_path,
        '''schema_version = 2

[[components]]
path = "escape"
[[components.workflows]]
suggested_commands = ["echo run"]
''',
    )

    with pytest.raises(WorkflowConfigError, match="outside the project root"):
        run_configured_workflow(tmp_path)


def test_duplicate_normalized_component_paths_are_rejected(tmp_path) -> None:
    write_config(
        tmp_path,
        '''schema_version = 2

[[components]]
path = "client"
[[components.workflows]]
suggested_commands = ["echo one"]

[[components]]
path = "client/../client"
[[components.workflows]]
suggested_commands = ["echo two"]
''',
    )

    with pytest.raises(WorkflowConfigError, match="duplicate component path 'client'"):
        run_configured_workflow(tmp_path)


def test_component_selection_normalizes_relative_path(tmp_path) -> None:
    component = tmp_path / "client"
    component.mkdir()
    write_config(
        tmp_path,
        '''schema_version = 2

[[components]]
path = "client"
[[components.workflows]]
suggested_commands = ["echo run"]
''',
    )
    process = Mock()
    process.wait.return_value = 0

    with patch("nex.execution.subprocess.Popen", return_value=process) as popen:
        assert run_configured_workflow(tmp_path, "client/../client") == 0

    popen.assert_called_once_with(("echo", "run"), cwd=component)


def test_missing_component_selection_is_an_error(tmp_path) -> None:
    write_config(
        tmp_path,
        '''schema_version = 2

[[components]]
path = "client"
[[components.workflows]]
suggested_commands = ["echo run"]
''',
    )

    with pytest.raises(WorkflowConfigError, match="No runnable workflow found"):
        run_configured_workflow(tmp_path, "server")


def test_component_without_runnable_workflow_is_not_selected(tmp_path) -> None:
    write_config(
        tmp_path,
        '''schema_version = 2

[[components]]
path = "client"
[[components.workflows]]
suggested_commands = []
''',
    )

    with pytest.raises(WorkflowConfigError, match="No runnable workflow found"):
        run_configured_workflow(tmp_path, "client")


def test_malformed_quoted_command_is_a_workflow_error(tmp_path) -> None:
    write_config(
        tmp_path,
        '''schema_version = 2

[[components]]
path = "."
[[components.workflows]]
suggested_commands = ['"unterminated']
''',
    )

    with pytest.raises(WorkflowConfigError, match="Invalid workflow command"):
        run_configured_workflow(tmp_path)


def test_embedded_nul_command_is_a_workflow_error(tmp_path) -> None:
    write_config(
        tmp_path,
        '''schema_version = 2

[[components]]
path = "."
[[components.workflows]]
suggested_commands = ["echo \\u0000"]
''',
    )

    with pytest.raises(WorkflowConfigError, match="Could not start workflow"):
        run_configured_workflow(tmp_path)


def test_real_subprocess_inherits_output_and_uses_component_cwd(tmp_path, capfd) -> None:
    component = tmp_path / "client"
    component.mkdir()
    command = shlex.join(
        [
            sys.executable,
            "-c",
            "import os,sys; print(os.getcwd()); print('stderr output', file=sys.stderr)",
        ]
    )
    write_config(
        tmp_path,
        f'''schema_version = 2

[[components]]
path = "client"
[[components.workflows]]
suggested_commands = [{json.dumps(command)}]
''',
    )

    assert run_configured_workflow(tmp_path) == 0
    captured = capfd.readouterr()
    assert str(component) in captured.out
    assert "stderr output" in captured.err


def test_real_subprocess_nonzero_exit_status_propagates(tmp_path) -> None:
    command = shlex.join([sys.executable, "-c", "raise SystemExit(23)"])
    write_config(
        tmp_path,
        f'''schema_version = 2

[[components]]
path = "."
[[components.workflows]]
suggested_commands = [{json.dumps(command)}]
''',
    )

    assert run_configured_workflow(tmp_path) == 23


def test_legacy_v1_config_executes_command_in_project_root(tmp_path) -> None:
    command = shlex.join([sys.executable, "-c", "raise SystemExit(17)"])
    write_config(
        tmp_path,
        f'''schema_version = 1

[frontend]
detected = true
command = {json.dumps(command)}
''',
    )

    assert run_configured_workflow(tmp_path) == 17


def test_ctrl_c_terminates_child_and_returns_130(tmp_path) -> None:
    write_config(
        tmp_path,
        """
schema_version = 2

[[components]]
path = "."
[[components.workflows]]
suggested_commands = ["npm run dev"]
""",
    )
    process = Mock()
    process.wait.side_effect = [KeyboardInterrupt, 0]

    with patch("nex.execution.subprocess.Popen", return_value=process):
        result = run_configured_workflow(tmp_path)

    assert result == 130
    process.terminate.assert_called_once_with()


def test_ctrl_c_when_child_already_exited_returns_130(tmp_path) -> None:
    write_config(
        tmp_path,
        '''schema_version = 2

[[components]]
path = "."
[[components.workflows]]
suggested_commands = ["echo run"]
''',
    )
    process = Mock()
    process.wait.side_effect = KeyboardInterrupt
    process.terminate.side_effect = ProcessLookupError

    with patch("nex.execution.subprocess.Popen", return_value=process):
        assert run_configured_workflow(tmp_path) == 130


def test_ctrl_c_timeout_kills_child_and_returns_130(tmp_path) -> None:
    write_config(
        tmp_path,
        '''schema_version = 2

[[components]]
path = "."
[[components.workflows]]
suggested_commands = ["echo run"]
''',
    )
    process = Mock()
    process.wait.side_effect = [
        KeyboardInterrupt,
        subprocess.TimeoutExpired("echo run", 5),
        0,
    ]

    with patch("nex.execution.subprocess.Popen", return_value=process):
        assert run_configured_workflow(tmp_path) == 130

    process.kill.assert_called_once_with()
