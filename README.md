# ADL Dictionary API

API for the [LexoTerm](https://github.com/adl-lex/adl-platform) research platform based on
[FastAPI](https://fastapi.tiangolo.com/).

## Development Setup

Requires [uv][uv].

- Clone the project
- Navigate to the project directory
- Run `uv sync`
- Create a `.env` file in the project root and set the following variables:

```env
MONGODB_URI="..."
API_UPLOAD_KEY="..."  # optional: only for uploading data (see below)
LEXOTERM_API_URL="..."
ALLOWED_ORIGINS="..."  # use semicolon ";" to separate multiple URLs
```

To start the development server, run `uv run poe dev`. The command loads the .env variables and
starts the fastapi app.

It is **strongly recommended** to configure your code editor to handle formatting and linting (cf.
the Code Quality section below). For example, to set up VS Code, install the [Ruff][ruffext]
extension and add the following contents to your .vscode/settings.json:

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

## Updating the Database

The api includes a POST endpoint to feed lexicographic data to the database without the need to log
into the server. Setup requires the `API_UPLOAD_KEY` environment variable to be set.

To upload transformed data to a fastapi instance, run:

```sh
# local/development
uv run poe upload path/to/transformed/bdo.json

# production
uv run poe upload --production path/to/transformed/bdo.json
```

> ⚠️ Note that this removes all existing data from the target collection!

## Code Quality

Code should adhere to the project's formatting and linting standards. We use:

- [Ruff](https://docs.astral.sh/ruff/) as linter and code formatter
- [Poe the Poet](https://poethepoet.natn.io/) for task handling

To run the formatter and linter manually:

```bash
# Format code with ruff
uv run poe format

# Lint code with ruff
uv run poe lint

# Run all checks (lint + format check)
uv run poe check
```

[uv]: https://docs.astral.sh/uv/getting-started/installation/
[ruffext]: https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff
