# ADL Dictionary API

API for the ADL platform based on [FastAPI](https://fastapi.tiangolo.com/).

## Setup

If you don't have it, you need to [install uv][uv].
Clone the project, navigate to adl-api/ and run `uv sync`. To start the development server, run
`uv run fastapi dev`.

It is strongly recommended to configure your code editor handle formatting and linting (cf. the
Code Quality section below). To configure VS Code, add the following contents to
.vscode/settings.json:

```json
{
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": "explicit",
      "source.organizeImports": "explicit"
    },
    "editor.defaultFormatter": "charliermarsh.ruff"
  },
  "ruff.nativeServer": true
}
```

## Code Quality

Code should adhere to the project's formatting and linting standards. We use:

- [Ruff](https://docs.astral.sh/ruff/) as linter and code formatter
- [Poe the Poet](https://poethepoet.natn.io/) for task handling

To run the formatter and linter manually.

```bash
# Format code with ruff
uv run poe format

# Lint code with ruff
uv run poe lint

# Run all checks (lint + format check)
uv run poe check
```

[uv]: https://docs.astral.sh/uv/getting-started/installation/
