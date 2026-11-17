# DeployForge backend (FastAPI + Docker SDK), dependencies installed with uv
FROM python:3.12-slim

# git is needed to clone the repositories that users deploy
RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl \
    && rm -rf /var/lib/apt/lists/* \
    && git config --system --add safe.directory '*'

# Copy the uv binary from Astral's official image (no pip install needed)
COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    DATA_DIR=/data

WORKDIR /app

# Install dependencies first so Docker can cache this layer.
# --no-dev skips pytest/httpx; --locked uses exactly the versions in uv.lock.
COPY pyproject.toml uv.lock* ./
RUN if [ -f uv.lock ]; then uv sync --locked --no-dev; else uv sync --no-dev; fi

# Use the virtual environment uv created in /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY app ./app

EXPOSE 8000

# Docker marks the container "healthy" when this command succeeds
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
    CMD curl -fs http://localhost:8000/api/health || exit 1

# Note: this container runs as root because it needs the Docker socket to
# build images. Deployed apps never get the socket (see docker_service.py).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
