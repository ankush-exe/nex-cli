# nex-cli

`nex-cli` is the command-line interface for Nex.

## Installation

Install the project in editable mode:

```bash
pip install -e .
```

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
