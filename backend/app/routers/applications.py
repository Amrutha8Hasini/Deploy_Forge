"""
Repository and application endpoints (Modules 2, 3, 4, 5 and 9).

/api/repositories/check   -> clone + detect + preview Dockerfile (nothing saved)
/api/applications         -> list / create applications
/api/applications/{id}/deploy   -> start the deployment pipeline
/api/applications/{id}/versions -> successful versions for rollback
/api/applications/{id}/rollback -> start an earlier image again
"""

import shutil
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.auth import require_user
from app.database import get_db
from app.models import Application, Deployment, DeploymentVersion
from app.routers.deployments import deployment_to_out
from app.schemas import (
    ApplicationCreate,
    ApplicationOut,
    BranchesRequest,
    DeploymentOut,
    RepoCheckRequest,
    RepoCheckResponse,
    RollbackRequest,
    VersionOut,
)
from app.services import deployment_service, docker_service
from app.services.detector import detect_project
from app.services.dockerfile_generator import generate_dockerfile
from app.services.github_service import (
    GitHubError,
    clone_repository,
    list_remote_branches,
    parse_github_url,
    resolve_source_dir,
    validate_branch,
)

router = APIRouter(prefix="/api", tags=["Applications"], dependencies=[Depends(require_user)])


# ------------------------------------------------------------ helpers ---


def get_application_or_404(db: Session, application_id: int) -> Application:
    application = db.get(Application, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


def container_states() -> dict[str, str]:
    """Map container name -> status for all DeployForge app containers."""
    try:
        return {c.name: c.status for c in docker_service.list_app_containers()}
    except Exception:  # noqa: BLE001 - Docker might be stopped; the page should still load
        return {}


def application_to_out(application: Application, states: dict[str, str]) -> ApplicationOut:
    out = ApplicationOut.model_validate(application)
    out.has_token = bool(application.github_token)
    if application.deployments:
        latest = application.deployments[0]  # newest first (see models.py)
        out.latest_status = latest.status
        out.latest_version = latest.version
    current = next((d for d in application.deployments if d.id == application.current_deployment_id), None)
    if current:
        out.container_status = states.get(current.container_name, "removed")
    return out


# ------------------------------------------------------- repositories ---


@router.post("/repositories/check", response_model=RepoCheckResponse)
def check_repository(body: RepoCheckRequest):
    """Fetch the repository once to show its name, type and Dockerfile."""
    workspace = config.WORKSPACE_DIR / "_checks" / uuid.uuid4().hex
    try:
        info = parse_github_url(body.repo_url)
        clone = clone_repository(body.repo_url, body.branch, workspace, body.github_token or config.GITHUB_TOKEN)
        source_dir = resolve_source_dir(clone.path, body.root_directory)
        detection = detect_project(source_dir)
        dockerfile = generate_dockerfile(detection) if detection.supported else ""
    except GitHubError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    return RepoCheckResponse(
        repo_owner=info.owner,
        repo_name=info.name,
        branch=body.branch,
        commit_id=clone.commit_id,
        commit_message=clone.commit_message,
        project_type=detection.project_type,
        supported=detection.supported,
        framework=detection.framework,
        message=detection.message,
        files_found=detection.files_found,
        dockerfile=dockerfile,
        internal_port=detection.internal_port,
    )


@router.post("/repositories/branches")
def get_branches(body: BranchesRequest):
    try:
        return {"branches": list_remote_branches(body.repo_url, body.github_token or config.GITHUB_TOKEN)}
    except GitHubError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ------------------------------------------------------- applications ---


@router.get("/applications", response_model=list[ApplicationOut])
def list_applications(db: Session = Depends(get_db)):
    states = container_states()
    applications = db.scalars(select(Application).order_by(Application.id.desc())).all()
    return [application_to_out(app, states) for app in applications]


@router.post("/applications", response_model=ApplicationOut, status_code=201)
def create_application(body: ApplicationCreate, db: Session = Depends(get_db)):
    try:
        info = parse_github_url(body.repo_url)
        branch = validate_branch(body.branch)
    except GitHubError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Docker image names must be lowercase, so we "slugify" the name
    name = deployment_service.slugify(body.name or info.name)
    if db.scalars(select(Application).where(Application.name == name)).first():
        raise HTTPException(status_code=409, detail=f"An application named '{name}' already exists")

    application = Application(
        name=name,
        repo_url=body.repo_url.strip(),
        repo_owner=info.owner,
        repo_name=info.name,
        branch=branch,
        root_directory=body.root_directory.strip().strip("/"),
        github_token=body.github_token.strip(),
        project_type=body.project_type,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application_to_out(application, {})


@router.get("/applications/{application_id}", response_model=ApplicationOut)
def get_application(application_id: int, db: Session = Depends(get_db)):
    return application_to_out(get_application_or_404(db, application_id), container_states())


@router.delete("/applications/{application_id}", status_code=204)
def delete_application(application_id: int, db: Session = Depends(get_db)):
    application = get_application_or_404(db, application_id)
    if deployment_service.has_active_deployment(db, application.id):
        raise HTTPException(status_code=409, detail="Wait for the running deployment to finish first")
    deployment_service.delete_application_resources(application)
    db.delete(application)
    db.commit()


# ----------------------------------------------------- deploy/rollback ---


@router.post("/applications/{application_id}/deploy", response_model=DeploymentOut, status_code=202)
def deploy_application(application_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    application = get_application_or_404(db, application_id)
    if deployment_service.has_active_deployment(db, application.id):
        raise HTTPException(status_code=409, detail="A deployment is already running for this application")

    deployment = deployment_service.create_deployment(db, application)
    # The pipeline takes a while, so it runs after we send the response.
    # The UI polls /api/deployments/{id}/logs to show live progress.
    background_tasks.add_task(deployment_service.run_deployment, deployment.id)
    return deployment_to_out(deployment)


@router.get("/applications/{application_id}/versions", response_model=list[VersionOut])
def list_versions(application_id: int, db: Session = Depends(get_db)):
    application = get_application_or_404(db, application_id)
    current = db.get(Deployment, application.current_deployment_id) if application.current_deployment_id else None
    result = []
    for version in application.versions:
        out = VersionOut.model_validate(version)
        try:
            out.image_available = docker_service.image_exists(version.image_tag)
        except docker_service.DockerUnavailableError:
            out.image_available = False
        out.is_current = bool(current and current.version == version.version)
        result.append(out)
    return result


@router.post("/applications/{application_id}/rollback", response_model=DeploymentOut, status_code=202)
def rollback_application(
    application_id: int, body: RollbackRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    application = get_application_or_404(db, application_id)
    version = db.get(DeploymentVersion, body.version_id)
    if not version or version.application_id != application.id:
        raise HTTPException(status_code=404, detail="Version not found")
    current = db.get(Deployment, application.current_deployment_id) if application.current_deployment_id else None
    if current and current.version == version.version:
        raise HTTPException(status_code=400, detail=f"{version.version} is already the live version")
    if deployment_service.has_active_deployment(db, application.id):
        raise HTTPException(status_code=409, detail="A deployment is already running for this application")

    deployment = deployment_service.create_rollback(db, application, version)
    background_tasks.add_task(deployment_service.run_rollback, deployment.id)
    return deployment_to_out(deployment)
