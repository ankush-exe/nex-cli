# nex-cli

`nex-cli` is the command-line interface for Nex.

## Installation

For normal use, install Nex from PyPI with [pipx](https://pipx.pypa.io/):

```bash
pipx install nex-cli
nex --version
```

The current release reports `nex 0.3.1`.

## Development

To work on Nex locally, clone the repository and install the development
dependencies in an isolated environment:

```bash
git clone https://github.com/ankush-exe/nex-cli.git
cd nex-cli
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
```

On Windows, activate the environment with `.venv\\Scripts\\activate` instead.

## Usage

```bash
nex learn                    # Discover the project and save workflow configuration
nex                         # Execute the saved workflow when one component is runnable
nex --component client      # Execute the workflow for the client component
nex learn --force           # Replace an existing Nex config
nex --help
nex --version
```

`nex learn` discovers and understands the project, then saves workflow
configuration to `.nex/config.toml`. For example, run `nex learn` from a
project root before running `nex`:

```bash
nex learn
nex
```

Bare `nex` reads the saved configuration and executes the workflow when exactly
one runnable component exists. If discovery finds multiple runnable components,
bare `nex` asks you to select one by its relative path:

```bash
nex --component client
```

Nex streams workflow output directly to the terminal, returns the workflow's
exit code, and maps Ctrl+C to exit code 130.

`nex learn` scans the current directory and up to three levels of child
directories, reports each detected project component, and saves the result to
`.nex/config.toml`. It detects `package.json`, `requirements.txt`,
`pyproject.toml`, and `docker-compose.yml`, while skipping common generated,
environment, dependency, and version-control directories.

For JavaScript components, Nex reports `dev` and `start` scripts and detects
the package manager from lockfiles for npm, pnpm, Yarn, or Bun. For Python
components, it records safe metadata such as the project name and Python
requirement from `pyproject.toml`. Malformed manifests are retained as detected
components and reported as warnings instead of stopping discovery. `nex learn`
does not install dependencies, modify project files, or start processes.

The generated configuration uses schema version 2 and records components,
signals, workflows, warnings, and deterministic suggested commands. Nex
refuses to replace an existing config unless you pass `--force`; this leaves
older v0.2.x schema version 1 files untouched until the user explicitly
chooses to replace them.

Nex v0.3.0 executes one workflow command at a time. It does not configure
environments, orchestrate multiple services, or supervise process trees. When
one component exposes more than one suggestion, Nex runs its first deterministic
suggestion (`dev` before `start`).

## Not yet

- Multi-service orchestration and process supervision
- Automatic workflow detection beyond the reported file signals
- Dependency installation

## License

Nex is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for the
full terms.

The `v0.1.0`, `v0.2.0`, and `v0.2.1` release tags and their distributed
artifacts remain available under their original MIT licenses. This change does
not revoke permissions already granted under those licenses.

---

© 2026 Ankush Thakur. All rights reserved.
