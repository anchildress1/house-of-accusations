FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    apt-get upgrade -y && \
    rm -rf /var/lib/apt/lists/*

ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN env UV_INSTALL_DIR="/usr/local/bin" sh /uv-installer.sh && rm /uv-installer.sh

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

RUN groupadd --system --gid 1001 appuser && \
    useradd --system --uid 1001 --gid appuser appuser && \
    chown -R appuser:appuser /app
USER appuser

ENV PORT=8080

CMD ["/app/.venv/bin/uvicorn", "house_of_accusations.main:app", "--host", "0.0.0.0", "--port", "8080"]
