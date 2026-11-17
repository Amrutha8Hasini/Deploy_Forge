"""
Application health checks.

After a container starts, we call the app over HTTP. We first try `/health`
(the convention our sample app follows) and fall back to `/` for apps without
a health endpoint. Any HTTP status below 500 means the app is answering.
"""

import time
from typing import Callable

import requests

from app import config

HEALTH_PATHS = ["/health", "/"]


def check_once(host_port: int, timeout: float = 3.0) -> tuple[bool, str]:
    """Call the app one time. Returns (is_healthy, short description)."""
    base_url = f"http://{config.HEALTH_CHECK_HOST}:{host_port}"
    last_error = ""
    for path in HEALTH_PATHS:
        try:
            response = requests.get(base_url + path, timeout=timeout)
            if response.status_code == 404 and path == "/health":
                continue  # app has no /health route, try "/"
            if response.status_code < 500:
                return True, f"GET {path} -> HTTP {response.status_code}"
            last_error = f"GET {path} -> HTTP {response.status_code}"
        except requests.RequestException as exc:
            last_error = f"GET {path} failed: {exc.__class__.__name__}"
            break  # connection refused: no point trying the next path yet
    return False, last_error


def wait_until_healthy(
    host_port: int,
    on_log: Callable[[str], None],
    is_container_running: Callable[[], bool],
    retries: int | None = None,
    interval: float | None = None,
) -> bool:
    """Try several times, because apps need a few seconds to start."""
    retries = retries or config.HEALTH_CHECK_RETRIES
    interval = config.HEALTH_CHECK_INTERVAL if interval is None else interval

    for attempt in range(1, retries + 1):
        healthy, detail = check_once(host_port)
        if healthy:
            on_log(f"Health check passed on attempt {attempt}: {detail}")
            return True
        if not is_container_running():
            on_log("Container stopped while starting. Check the application logs.")
            return False
        on_log(f"Attempt {attempt}/{retries}: not ready yet ({detail})")
        time.sleep(interval)
    return False
