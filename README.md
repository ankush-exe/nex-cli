# nex-cli

`nex-cli` is the command-line interface for Nex.

## Installation

For normal use, install Nex from PyPI with [pipx](https://pipx.pypa.io/):

```bash
pipx install nex-cli
nex --version
```

The current release reports `nex 0.2.1`.

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
nex --help
nex --version
nex learn          # Detect and save project signals
nex learn --force  # Replace an existing Nex config
```

Running `nex` without arguments displays help and exits successfully.

`nex learn` inspects the current directory, reports common project signals, and
saves them to `.nex/config.toml`. It detects:
`package.json` (including `dev` and `start` scripts), `requirements.txt`,
`pyproject.toml`, and `docker-compose.yml`.

The config records the project root, a future-ready frontend command such as
`npm run dev`, backend file signals, and Docker Compose presence. Nex refuses
to replace an existing config unless you pass `--force`.

## Not yet

- Running or supervising development processes
- Automatic workflow detection beyond the reported file signals
- Reading saved configuration to start a project

## License

Nex is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for the
full terms.

The `v0.1.0`, `v0.2.0`, and `v0.2.1` release tags and their distributed
artifacts remain available under their original MIT licenses. This change does
not revoke permissions already granted under those licenses.
