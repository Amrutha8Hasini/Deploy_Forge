# DeployForge backend (FastAPI + Docker SDK)
FROM python:3.12-slim

# git is needed to clone the repositories that users deploy
RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl \
    && rm -rf /var/lib/apt/lists/* \
    && git config --system --add safe.directory '*'

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/data

WORKDIR /app

# Install Python packages first so Docker can cache this layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

# Docker marks the container "healthy" when this command succeeds
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
    CMD curl -fs http://localhost:8000/api/health || exit 1

# Note: this container runs as root because it needs the Docker socket to
# build images. Deployed apps never get the socket (see docker_service.py).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
