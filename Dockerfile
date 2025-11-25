FROM ghcr.io/astral-sh/uv:python3.10-alpine

WORKDIR /code

COPY . /code

RUN uv sync --locked --no-dev

CMD ["uv", "run", "fastapi", "run", "app/main.py", "--proxy-headers", "--port", "80"]
