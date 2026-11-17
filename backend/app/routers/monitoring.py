"""Dashboard numbers, monitoring and settings (Modules 1 and 10)."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import config
from app.auth import require_user
from app.database import get_db
from app.models import Application, Deployment, DeployStatus
from app.routers.deployments import deployment_to_out
from app.services import docker_service, health_checker
from app.services.stats import calculate_stats

router = APIRouter(prefix="/api", tags=["Monitoring"], dependencies=[Depends(require_user)])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    total_apps = db.scalar(select(func.count(Application.id))) or 0
    # "Replaced" and "Rolled Back" deployments were also successful when they ran
    finished_ok = [DeployStatus.SUCCESSFUL, DeployStatus.REPLACED, DeployStatus.ROLLED_BACK]
    successful = db.scalar(select(func.count(Deployment.id)).where(Deployment.status.in_(finished_ok))) or 0
    failed = db.scalar(select(func.count(Deployment.id)).where(Deployment.status == DeployStatus.FAILED)) or 0

    docker_ok = True
    try:
        running = sum(1 for c in docker_service.list_app_containers() if c.status == "running")
    except docker_service.DockerUnavailableError:
        running, docker_ok = 0, False

    # Deployments per day for the last 7 days (for the bar chart)
    today = datetime.now(timezone.utc).date()
    since = datetime.combine(today - timedelta(days=6), datetime.min.time())
    per_day = {(today - timedelta(days=i)).isoformat(): {"successful": 0, "failed": 0} for i in range(6, -1, -1)}
    for deployment in db.scalars(select(Deployment).where(Deployment.created_at >= since)):
        day = deployment.created_at.date().isoformat()
        if day in per_day and deployment.finished_at:
            key = "failed" if deployment.status == DeployStatus.FAILED else "successful"
            per_day[day][key] += 1

    recent = db.scalars(select(Deployment).order_by(Deployment.id.desc()).limit(8)).all()
    return {
        "total_applications": total_apps,
        "successful_deployments": successful,
        "failed_deployments": failed,
        "running_containers": running,
        "docker_available": docker_ok,
        "deployments_per_day": [{"date": day, **counts} for day, counts in per_day.items()],
        "recent_deployments": [deployment_to_out(d) for d in recent],
    }


def _monitor_one(container) -> dict:
    """Collect status, CPU/memory and health for one container."""
    summary = docker_service.container_summary(container)
    summary["stats"] = None
    summary["health"] = "Stopped"
    summary["health_detail"] = ""
    if container.status == "running":
        try:
            summary["stats"] = calculate_stats(container.stats(stream=False))
        except Exception:  # noqa: BLE001
            summary["stats"] = None
        if summary["host_port"]:
            healthy, detail = health_checker.check_once(summary["host_port"], timeout=2)
            summary["health"] = "Healthy" if healthy else "Unhealthy"
            summary["health_detail"] = detail
    return summary


@router.get("/monitoring")
def monitoring():
    try:
        containers = docker_service.list_app_containers()
    except docker_service.DockerUnavailableError as exc:
        return {"docker_available": False, "error": str(exc), "containers": []}
    # Reading stats takes about 1 second per container, so do them in parallel
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(_monitor_one, containers))
    return {"docker_available": True, "containers": results}


@router.get("/settings")
def settings():
    return {
        "docker": docker_service.docker_info(),
        "github_token_configured": bool(config.GITHUB_TOKEN),
        "public_host": config.PUBLIC_HOST,
        "health_check_host": config.HEALTH_CHECK_HOST,
        "port_range": f"{config.APP_PORT_START}-{config.APP_PORT_END}",
        "apps_network": config.APPS_NETWORK,
        "memory_limit": config.APP_MEMORY_LIMIT,
        "cpu_limit": config.APP_CPU_LIMIT,
        "admin_username": config.ADMIN_USERNAME,
    }
