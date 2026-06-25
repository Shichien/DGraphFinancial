FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md config.toml /app/
COPY src /app/src

RUN pip install --no-cache-dir uv \
    && uv pip install --system .

CMD ["dgcheater-stream", "--help"]
