FROM ghcr.io/astral-sh/uv:python3.10-alpine

WORKDIR /code

RUN apk add --no-cache mongodb-tools

COPY . /code

RUN uv sync --locked --no-dev

CMD ["uv", "run", "fastapi", "run", "app/main.py", "--proxy-headers", "--port", "80"]
