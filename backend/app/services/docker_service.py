"""
Docker operations using the official Docker SDK for Python.

Everything here talks to the real Docker Engine (Docker Desktop on a Mac).
Nothing is simulated.

Safety rules:
* Every image and container we create gets the label `deployforge.managed=true`.
* Container actions (start/stop/restart/logs/remove) refuse to touch any
  container without that label, so the user's other containers are safe.
* Deployed apps run with memory/CPU limits, no extra Linux capabilities,
  no Docker socket and on their own network.
"""

from typing import Callable

import docker
from docker.errors import APIError, DockerException, ImageNotFound, NotFound

from app import config
from app.services.stats import calculate_stats

LogCallback = Callable[[str], None]

_client: docker.DockerClient | None = None


class DockerUnavailableError(Exception):
    """Docker Desktop is not running or not reachable."""


class DockerBuildError(Exception):
    """`docker build` failed. The message contains Docker's error."""


class ContainerNotManagedError(Exception):
    """Someone tried to control a container that DeployForge did not create."""


def get_client() -> docker.DockerClient:
    """Connect to Docker once and reuse the connection."""
    global _client
    if _client is None:
        try:
            _client = docker.from_env()
            _client.ping()
        except DockerException as exc:
            _client = None
            raise DockerUnavailableError(
                "Cannot connect to Docker. Make sure Docker Desktop is running."
            ) from exc
    return _client


def docker_info() -> dict:
    """Small summary of the Docker Engine, shown on the Settings page."""
    try:
        info = get_client().info()
        return {
            "available": True,
            "server_version": info.get("ServerVersion", ""),
            "containers_running": info.get("ContainersRunning", 0),
            "images": info.get("Images", 0),
            "os": info.get("OperatingSystem", ""),
            "cpus": info.get("NCPU", 0),
            "memory_gb": round(info.get("MemTotal", 0) / (1024**3), 1),
        }
    except (DockerUnavailableError, DockerException) as exc:
        return {"available": False, "error": str(exc)}


# ---------------------------------------------------------------- images ---


def build_image(context_dir: str, dockerfile_name: str, tag: str, labels: dict, on_log: LogCallback) -> None:
    """Build an image and send every line of Docker's output to `on_log`.

    We use the low-level API (`client.api.build`) because it streams the build
    output line by line, which lets the UI show real build logs.
    """
    client = get_client()
    stream = client.api.build(
        path=context_dir,
        dockerfile=dockerfile_name,
        tag=tag,
        labels={config.MANAGED_LABEL: "true", **labels},
        rm=True,  # remove temporary containers after a successful build
        forcerm=True,  # ...and after a failed build
        decode=True,  # give us Python dicts instead of raw bytes
    )
    for chunk in stream:
        if "stream" in chunk:
            line = chunk["stream"].rstrip()
            if line:
                on_log(line)
        elif "status" in chunk:  # e.g. pulling the base image
            on_log(f"{chunk['status']} {chunk.get('progress', '')}".strip())
        if "error" in chunk:
            raise DockerBuildError(chunk["error"].strip())


def image_exists(tag: str) -> bool:
    try:
        get_client().images.get(tag)
        return True
    except ImageNotFound:
        return False


def remove_image(tag: str) -> None:
    try:
        get_client().images.remove(tag, force=True)
    except (ImageNotFound, APIError):
        pass


# ------------------------------------------------------------ containers ---


def ensure_apps_network() -> None:
    """Create the separate network for deployed apps if it does not exist."""
    client = get_client()
    if not client.networks.list(names=[config.APPS_NETWORK]):
        client.networks.create(config.APPS_NETWORK, driver="bridge", labels={config.MANAGED_LABEL: "true"})


def used_host_ports() -> set[int]:
    """Host ports already published by ANY container on this machine."""
    ports: set[int] = set()
    for container in get_client().containers.list(all=True):
        bindings = (container.attrs.get("HostConfig") or {}).get("PortBindings") or {}
        for host_list in bindings.values():
            for binding in host_list or []:
                if binding.get("HostPort", "").isdigit():
                    ports.add(int(binding["HostPort"]))
    return ports


def run_app_container(
    image_tag: str, container_name: str, host_port: int, internal_port: int, labels: dict
):
    """Start a deployed application with basic security restrictions."""
    ensure_apps_network()
    return get_client().containers.run(
        image_tag,
        name=container_name,
        detach=True,
        ports={f"{internal_port}/tcp": host_port},
        environment={"PORT": str(internal_port)},
        labels={config.MANAGED_LABEL: "true", "deployforge.role": "app", **labels},
        network=config.APPS_NETWORK,
        # --- basic security restrictions ---
        mem_limit=config.APP_MEMORY_LIMIT,
        nano_cpus=int(config.APP_CPU_LIMIT * 1_000_000_000),
        pids_limit=200,
        cap_drop=["ALL"],
        security_opt=["no-new-privileges:true"],
        # restart the app if it crashes (at most 3 times)
        restart_policy={"Name": "on-failure", "MaximumRetryCount": 3},
    )


def remove_container_if_exists(name_or_id: str) -> None:
    try:
        get_client().containers.get(name_or_id).remove(force=True)
    except NotFound:
        pass


def get_managed_container(name_or_id: str):
    """Find a container and make sure DeployForge created it."""
    try:
        container = get_client().containers.get(name_or_id)
    except NotFound as exc:
        raise NotFound(f"Container {name_or_id} not found") from exc
    if container.labels.get(config.MANAGED_LABEL) != "true":
        raise ContainerNotManagedError("DeployForge only controls containers it created")
    return container


def list_app_containers() -> list:
    return get_client().containers.list(all=True, filters={"label": "deployforge.role=app"})


def container_summary(container) -> dict:
    """Turn a Docker container object into a simple dictionary for the API."""
    labels = container.labels
    host_port = labels.get("deployforge.host_port", "")
    return {
        "id": container.short_id,
        "name": container.name,
        "status": container.status,  # running, exited, created, restarting ...
        "image": labels.get("deployforge.image", ""),
        "application": labels.get("deployforge.app", ""),
        "version": labels.get("deployforge.version", ""),
        "deployment_id": int(labels["deployforge.deployment_id"]) if labels.get("deployforge.deployment_id", "").isdigit() else None,
        "host_port": int(host_port) if host_port.isdigit() else None,
        "url": f"http://{config.PUBLIC_HOST}:{host_port}" if host_port else "",
        "created": container.attrs.get("Created", ""),
    }


def container_logs(name_or_id: str, tail: int = 200) -> str:
    container = get_managed_container(name_or_id)
    return container.logs(tail=tail, timestamps=False).decode("utf-8", errors="replace")


def start_container(name_or_id: str) -> None:
    get_managed_container(name_or_id).start()


def stop_container(name_or_id: str) -> None:
    get_managed_container(name_or_id).stop(timeout=5)


def restart_container(name_or_id: str) -> None:
    get_managed_container(name_or_id).restart(timeout=5)


# ------------------------------------------------------------ monitoring ---


def container_stats(name_or_id: str) -> dict:
    container = get_managed_container(name_or_id)
    if container.status != "running":
        return {"cpu_percent": 0.0, "memory_used_mb": 0.0, "memory_limit_mb": 0.0, "memory_percent": 0.0}
    raw = container.stats(stream=False)  # one snapshot (Docker waits ~1 s to compare)
    return calculate_stats(raw)
