"""Docker container management (Module 6)."""

from docker.errors import APIError, NotFound
from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_user
from app.services import docker_service

router = APIRouter(prefix="/api/containers", tags=["Containers"], dependencies=[Depends(require_user)])


def run_docker_action(action, name: str):
    """Call a Docker function and turn Docker errors into clear HTTP errors."""
    try:
        return action(name)
    except docker_service.DockerUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except docker_service.ContainerNotManagedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except NotFound as exc:
        raise HTTPException(status_code=404, detail=f"Container {name} not found") from exc
    except APIError as exc:
        raise HTTPException(status_code=400, detail=exc.explanation or str(exc)) from exc


@router.get("")
def list_containers():
    try:
        return [docker_service.container_summary(c) for c in docker_service.list_app_containers()]
    except docker_service.DockerUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/{name}/logs")
def get_logs(name: str, tail: int = 200):
    logs = run_docker_action(lambda n: docker_service.container_logs(n, tail=min(tail, 2000)), name)
    return {"name": name, "logs": logs}


@router.get("/{name}/stats")
def get_stats(name: str):
    return run_docker_action(docker_service.container_stats, name)


@router.post("/{name}/start")
def start(name: str):
    run_docker_action(docker_service.start_container, name)
    return {"name": name, "action": "started"}


@router.post("/{name}/stop")
def stop(name: str):
    run_docker_action(docker_service.stop_container, name)
    return {"name": name, "action": "stopped"}


@router.post("/{name}/restart")
def restart(name: str):
    run_docker_action(docker_service.restart_container, name)
    return {"name": name, "action": "restarted"}
