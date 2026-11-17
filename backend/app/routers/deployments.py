"""Deployment history and build logs (Modules 5 and 8)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_user
from app.database import get_db
from app.models import BuildLog, Deployment
from app.schemas import BuildLogOut, DeploymentDetail, DeploymentOut

router = APIRouter(prefix="/api/deployments", tags=["Deployments"], dependencies=[Depends(require_user)])


def deployment_to_out(deployment: Deployment, detail: bool = False) -> DeploymentOut:
    schema = DeploymentDetail if detail else DeploymentOut
    out = schema.model_validate(deployment)
    out.application_name = deployment.application.name
    out.is_current = deployment.application.current_deployment_id == deployment.id
    return out


@router.get("", response_model=list[DeploymentOut])
def list_deployments(application_id: int | None = None, limit: int = 100, db: Session = Depends(get_db)):
    query = select(Deployment).order_by(Deployment.id.desc()).limit(min(limit, 500))
    if application_id:
        query = query.where(Deployment.application_id == application_id)
    return [deployment_to_out(d) for d in db.scalars(query)]


@router.get("/{deployment_id}", response_model=DeploymentDetail)
def get_deployment(deployment_id: int, db: Session = Depends(get_db)):
    deployment = db.get(Deployment, deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return deployment_to_out(deployment, detail=True)


@router.get("/{deployment_id}/logs", response_model=list[BuildLogOut])
def get_build_logs(deployment_id: int, after_id: int = 0, db: Session = Depends(get_db)):
    """Return log lines. `after_id` lets the UI fetch only new lines while polling."""
    if not db.get(Deployment, deployment_id):
        raise HTTPException(status_code=404, detail="Deployment not found")
    query = (
        select(BuildLog)
        .where(BuildLog.deployment_id == deployment_id, BuildLog.id > after_id)
        .order_by(BuildLog.id)
    )
    return db.scalars(query).all()
