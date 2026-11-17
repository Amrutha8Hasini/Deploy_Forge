"""
Application settings.

All settings are read from environment variables so that the same code can run
on a laptop (`uvicorn app.main:app`) and inside Docker Compose. Default values
are chosen so that the backend works with no configuration at all.
"""

import os
from pathlib import Path

# Folder that holds the backend code (".../backend")
BACKEND_DIR = Path(__file__).resolve().parent.parent

# Where we keep the SQLite file and the cloned repositories
DATA_DIR = Path(os.getenv("DATA_DIR", BACKEND_DIR / "data"))
WORKSPACE_DIR = Path(os.getenv("WORKSPACE_DIR", DATA_DIR / "workspaces"))

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'deployforge.db'}")

# --- Login (kept intentionally simple: one admin account) ---
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")

# --- GitHub ---
# Optional default token, used for private repositories when an application
# does not have its own token.
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# --- Deployed applications ---
# Host ports that DeployForge may give to deployed apps (inclusive range).
APP_PORT_START = int(os.getenv("APP_PORT_START", "8100"))
APP_PORT_END = int(os.getenv("APP_PORT_END", "8199"))

# Host name used in the URL shown to the user (what you type in the browser).
PUBLIC_HOST = os.getenv("PUBLIC_HOST", "localhost")

# Host name the backend uses for health checks. When the backend runs directly
# on the Mac this is "localhost". Inside Docker Compose the backend is itself a
# container, so it must use "host.docker.internal" to reach the host's ports.
HEALTH_CHECK_HOST = os.getenv("HEALTH_CHECK_HOST", "localhost")

# Separate Docker network for deployed apps (keeps them away from the platform).
APPS_NETWORK = os.getenv("APPS_NETWORK", "deployforge-apps")

# Resource limits applied to every deployed container (basic security).
APP_MEMORY_LIMIT = os.getenv("APP_MEMORY_LIMIT", "256m")
APP_CPU_LIMIT = float(os.getenv("APP_CPU_LIMIT", "0.5"))  # number of CPUs

# Health check: how many times to try, and how long to wait between tries.
HEALTH_CHECK_RETRIES = int(os.getenv("HEALTH_CHECK_RETRIES", "15"))
HEALTH_CHECK_INTERVAL = float(os.getenv("HEALTH_CHECK_INTERVAL", "2"))

# Frontend address allowed to call the API from the browser (CORS).
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

# Label put on every container/image DeployForge creates, so we only ever
# touch our own containers and never the user's other containers.
MANAGED_LABEL = "deployforge.managed"


def ensure_data_dirs() -> None:
    """Create the data folders if they do not exist yet."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
