"""
The deployment pipeline. This is the heart of DeployForge.

When the user clicks Deploy, `run_deployment` runs in the background and goes
through these steps, writing a log line for each one:

    1. Fetch the repository from GitHub (git clone)
    2. Detect the project type
    3. Generate a Dockerfile
    4. Build a Docker image (real build logs are saved)
    5. Start a container on a free local port
    6. Health check the application
    7. If healthy: make it the live version and stop the old container
       If not healthy: remove the new container and keep the old one running

Rollback re-uses steps 5 to 7 with an image that was built earlier.
"""

import re
import shutil
import traceback

from docker.errors import APIError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.database import SessionLocal
from app.models import Application, BuildLog, BuildStatus, Deployment, DeploymentVersion, DeployStatus, utc_now
from app.services import docker_service, health_checker
from app.services.detector import detect_project
from app.services.dockerfile_generator import GENERATED_DOCKERFILE_NAME, generate_dockerfile, write_dockerfile
from app.services.github_service import clone_repository, resolve_source_dir

ACTIVE_STATUSES = [DeployStatus.PENDING, DeployStatus.DEPLOYING]


class DeploymentError(Exception):
    """A step failed. The message is shown to the user."""


# --------------------------------------------------------------- helpers ---


def slugify(text: str) -> str:
    """Make a Docker-safe name: lowercase letters, numbers and dashes."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:50] or "app"


def add_log(db: Session, deployment: Deployment, step: str, message: str, level: str = "info") -> None:
    db.add(BuildLog(deployment_id=deployment.id, step=step, message=message, level=level))
    db.commit()


def next_version(db: Session, application: Application) -> str:
    """v1, v2, v3 ... counting only real builds (not rollbacks)."""
    builds = db.scalars(
        select(Deployment).where(Deployment.application_id == application.id, Deployment.is_rollback.is_(False))
    ).all()
    return f"v{len(builds) + 1}"


def has_active_deployment(db: Session, application_id: int) -> bool:
    active = db.scalars(
        select(Deployment).where(Deployment.application_id == application_id, Deployment.status.in_(ACTIVE_STATUSES))
    ).first()
    return active is not None


def find_free_port() -> int:
    used = docker_service.used_host_ports()
    for port in range(config.APP_PORT_START, config.APP_PORT_END + 1):
        if port not in used:
            return port
    raise DeploymentError(f"No free port between {config.APP_PORT_START} and {config.APP_PORT_END}")


def mark_interrupted_deployments() -> None:
    """Called at start-up: deployments that were running when the server
    stopped can never finish, so mark them as failed."""
    with SessionLocal() as db:
        for deployment in db.scalars(select(Deployment).where(Deployment.status.in_(ACTIVE_STATUSES))):
            deployment.status = DeployStatus.FAILED
            if deployment.build_status in (BuildStatus.PENDING, BuildStatus.BUILDING):
                deployment.build_status = BuildStatus.FAILED
            deployment.error_message = "Interrupted because the server restarted."
            deployment.finished_at = utc_now()
        db.commit()


# ---------------------------------------------------------- create rows ---


def create_deployment(db: Session, application: Application) -> Deployment:
    deployment = Deployment(
        application_id=application.id,
        version=next_version(db, application),
        project_type=application.project_type,
        build_status=BuildStatus.PENDING,
        status=DeployStatus.PENDING,
    )
    db.add(deployment)
    db.commit()
    db.refresh(deployment)
    return deployment


def create_rollback(db: Session, application: Application, version: DeploymentVersion) -> Deployment:
    current = db.get(Deployment, application.current_deployment_id) if application.current_deployment_id else None
    original = db.get(Deployment, version.deployment_id)
    deployment = Deployment(
        application_id=application.id,
        version=version.version,
        commit_id=version.commit_id,
        commit_message=original.commit_message if original else "",
        project_type=version.project_type,
        dockerfile=original.dockerfile if original else "",
        image_tag=version.image_tag,
        build_status=BuildStatus.SUCCESSFUL,  # nothing to build: we re-use the old image
        status=DeployStatus.PENDING,
        is_rollback=True,
        rollback_from_version=current.version if current else "",
    )
    db.add(deployment)
    db.commit()
    db.refresh(deployment)
    return deployment


# -------------------------------------------------------------- pipeline ---


def run_deployment(deployment_id: int) -> None:
    """Background task for a normal deployment (steps 1-7)."""
    with SessionLocal() as db:
        deployment = db.get(Deployment, deployment_id)
        application = deployment.application
        workspace = config.WORKSPACE_DIR / application.name / str(deployment.id)

        try:
            deployment.status = DeployStatus.DEPLOYING
            deployment.build_status = BuildStatus.BUILDING
            db.commit()

            # Step 1: fetch the repository
            add_log(db, deployment, "clone", f"Cloning {application.repo_url} (branch: {application.branch})")
            token = application.github_token or config.GITHUB_TOKEN
            clone = clone_repository(application.repo_url, application.branch, workspace, token)
            deployment.commit_id = clone.commit_id
            deployment.commit_message = clone.commit_message
            db.commit()
            add_log(db, deployment, "clone", f"Fetched commit {clone.commit_id[:7]}: {clone.commit_message}", "success")
            source_dir = resolve_source_dir(clone.path, application.root_directory)

            # Step 2: detect the project type
            detection = detect_project(source_dir)
            add_log(db, deployment, "detect", f"Files found: {', '.join(detection.files_found) or 'none'}")
            if not detection.supported:
                raise DeploymentError(detection.message)
            deployment.project_type = detection.project_type
            application.project_type = detection.project_type
            db.commit()
            add_log(db, deployment, "detect", detection.message, "success")

            # Step 3: generate the Dockerfile
            dockerfile_text = generate_dockerfile(detection)
            write_dockerfile(source_dir, dockerfile_text)
            deployment.dockerfile = dockerfile_text
            db.commit()
            add_log(db, deployment, "dockerfile", f"Generated {GENERATED_DOCKERFILE_NAME} ({detection.project_type})", "success")

            # Step 4: build the image
            image_tag = f"deployforge/{application.name}:{deployment.version}"
            deployment.image_tag = image_tag
            db.commit()
            add_log(db, deployment, "build", f"Building Docker image {image_tag}")
            docker_service.build_image(
                str(source_dir),
                GENERATED_DOCKERFILE_NAME,
                image_tag,
                labels={"deployforge.app": application.name, "deployforge.version": deployment.version},
                on_log=lambda line: add_log(db, deployment, "build", line),
            )
            deployment.build_status = BuildStatus.SUCCESSFUL
            db.commit()
            add_log(db, deployment, "build", f"Image {image_tag} built successfully", "success")

            # Steps 5-7: run, health check, switch traffic
            start_and_verify(db, deployment, detection.internal_port)

        except Exception as exc:  # noqa: BLE001 - every error must be shown to the user
            fail_deployment(db, deployment, exc)
        finally:
            shutil.rmtree(workspace, ignore_errors=True)  # the source code is no longer needed


def run_rollback(deployment_id: int) -> None:
    """Background task for a rollback: start an earlier image again."""
    with SessionLocal() as db:
        deployment = db.get(Deployment, deployment_id)
        try:
            deployment.status = DeployStatus.DEPLOYING
            db.commit()
            add_log(db, deployment, "rollback", f"Rolling back to {deployment.version} using image {deployment.image_tag}")
            if not docker_service.image_exists(deployment.image_tag):
                raise DeploymentError(f"Image {deployment.image_tag} no longer exists, cannot roll back")
            add_log(db, deployment, "rollback", "Image found locally. Skipping clone and build.", "success")
            internal_port = 3000 if deployment.project_type == "node" else 8000
            start_and_verify(db, deployment, internal_port)
        except Exception as exc:  # noqa: BLE001
            fail_deployment(db, deployment, exc)


def start_and_verify(db: Session, deployment: Deployment, internal_port: int) -> None:
    """Steps 5-7: start the container, check its health, make it live."""
    application = deployment.application
    container_name = f"deployforge-{application.name}-{deployment.version}-d{deployment.id}"
    docker_service.remove_container_if_exists(container_name)

    # Step 5: start the container on a free port. If another program grabbed
    # the port in the meantime, try the next free one.
    container = None
    for _attempt in range(5):
        host_port = find_free_port()
        labels = {
            "deployforge.app": application.name,
            "deployforge.version": deployment.version,
            "deployforge.deployment_id": str(deployment.id),
            "deployforge.host_port": str(host_port),
            "deployforge.image": deployment.image_tag,
        }
        try:
            container = docker_service.run_app_container(
                deployment.image_tag, container_name, host_port, internal_port, labels
            )
            break
        except APIError as exc:
            docker_service.remove_container_if_exists(container_name)
            if "port is already allocated" in str(exc) or "address already in use" in str(exc):
                add_log(db, deployment, "run", f"Port {host_port} is busy, trying another port")
                continue
            raise
    if container is None:
        raise DeploymentError("Could not find a free port to start the container")

    deployment.container_name = container_name
    deployment.container_id = container.id
    deployment.host_port = host_port
    deployment.url = f"http://{config.PUBLIC_HOST}:{host_port}"
    db.commit()
    add_log(db, deployment, "run", f"Started container {container_name} on port {host_port}", "success")

    # Step 6: health check
    add_log(db, deployment, "health", "Waiting for the application to respond...")

    def is_running() -> bool:
        container.reload()
        return container.status in ("running", "restarting", "created")

    healthy = health_checker.wait_until_healthy(
        host_port, on_log=lambda line: add_log(db, deployment, "health", line), is_container_running=is_running
    )

    if not healthy:
        # Save the app's own output so the user can see why it failed
        logs = container.logs(tail=30).decode("utf-8", errors="replace").strip()
        if logs:
            add_log(db, deployment, "health", "Last application output:\n" + logs, "error")
        docker_service.remove_container_if_exists(container_name)
        raise DeploymentError("Health check failed. The previous version (if any) is still running.")

    # Step 7: the new version is live. Stop the old one.
    previous_id = application.current_deployment_id
    if previous_id and previous_id != deployment.id:
        previous = db.get(Deployment, previous_id)
        if previous:
            docker_service.remove_container_if_exists(previous.container_name)
            previous.status = DeployStatus.ROLLED_BACK if deployment.is_rollback else DeployStatus.REPLACED
            previous.health_status = "Stopped"
            add_log(db, deployment, "switch", f"Stopped previous version {previous.version} ({previous.container_name})")

    if not deployment.is_rollback:
        db.add(
            DeploymentVersion(
                application_id=application.id,
                deployment_id=deployment.id,
                version=deployment.version,
                image_tag=deployment.image_tag,
                commit_id=deployment.commit_id,
                project_type=deployment.project_type,
            )
        )

    deployment.status = DeployStatus.SUCCESSFUL
    deployment.health_status = "Healthy"
    deployment.finished_at = utc_now()
    application.current_deployment_id = deployment.id
    application.current_url = deployment.url
    db.commit()
    add_log(db, deployment, "done", f"Deployment successful! Open {deployment.url}", "success")


def fail_deployment(db: Session, deployment: Deployment, exc: Exception) -> None:
    db.rollback()  # discard half-finished changes from the failed step
    if "Health check failed" in str(exc):
        deployment.health_status = "Unhealthy"
    if deployment.build_status in (BuildStatus.PENDING, BuildStatus.BUILDING):
        deployment.build_status = BuildStatus.FAILED
    deployment.status = DeployStatus.FAILED
    deployment.error_message = str(exc) or exc.__class__.__name__
    deployment.finished_at = utc_now()
    db.commit()
    add_log(db, deployment, "error", f"Deployment failed: {deployment.error_message}", "error")
    if not isinstance(exc, DeploymentError):
        # Unexpected errors: keep the technical details in the server log
        traceback.print_exc()


def delete_application_resources(application: Application) -> None:
    """Remove the containers and images that belong to an application."""
    try:
        for container in docker_service.list_app_containers():
            if container.labels.get("deployforge.app") == application.name:
                container.remove(force=True)
        for version in application.versions:
            docker_service.remove_image(version.image_tag)
    except docker_service.DockerUnavailableError:
        pass  # Docker is off: just delete the database rows
