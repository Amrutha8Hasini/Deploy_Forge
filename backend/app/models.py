"""
Database tables (SQLAlchemy models).

applications         -> one row per connected GitHub repository
deployments          -> one row every time the user clicks Deploy (or rolls back)
build_logs           -> the log lines produced while a deployment runs
deployment_versions  -> successful Docker images we can roll back to
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# Status values used across the project (kept as plain strings so they are
# easy to read in the database and in the UI).
class BuildStatus:
    PENDING = "Pending"
    BUILDING = "Building"
    SUCCESSFUL = "Successful"
    FAILED = "Failed"


class DeployStatus:
    PENDING = "Pending"
    DEPLOYING = "Deploying"
    SUCCESSFUL = "Successful"
    FAILED = "Failed"
    ROLLED_BACK = "Rolled Back"  # this deployment was replaced by a rollback
    REPLACED = "Replaced"  # this deployment was replaced by a newer deploy


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)  # e.g. "deployforge-sample"
    repo_url: Mapped[str] = mapped_column(String(300))
    repo_owner: Mapped[str] = mapped_column(String(100), default="")
    repo_name: Mapped[str] = mapped_column(String(100), default="")
    branch: Mapped[str] = mapped_column(String(100), default="main")
    root_directory: Mapped[str] = mapped_column(String(200), default="")  # sub-folder of the repo
    github_token: Mapped[str] = mapped_column(String(300), default="")  # never returned by the API
    project_type: Mapped[str] = mapped_column(String(30), default="unknown")  # python / node
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    # Information about what is currently live
    current_deployment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_url: Mapped[str] = mapped_column(String(200), default="")

    deployments: Mapped[list["Deployment"]] = relationship(
        back_populates="application", cascade="all, delete-orphan", order_by="Deployment.id.desc()"
    )
    versions: Mapped[list["DeploymentVersion"]] = relationship(
        back_populates="application", cascade="all, delete-orphan", order_by="DeploymentVersion.id.desc()"
    )


class Deployment(Base):
    __tablename__ = "deployments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"))
    version: Mapped[str] = mapped_column(String(20), default="")  # "v1", "v2", ...
    commit_id: Mapped[str] = mapped_column(String(40), default="")
    commit_message: Mapped[str] = mapped_column(String(300), default="")
    project_type: Mapped[str] = mapped_column(String(30), default="")
    dockerfile: Mapped[str] = mapped_column(Text, default="")  # the generated Dockerfile
    image_tag: Mapped[str] = mapped_column(String(200), default="")
    container_name: Mapped[str] = mapped_column(String(200), default="")
    container_id: Mapped[str] = mapped_column(String(80), default="")
    host_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    url: Mapped[str] = mapped_column(String(200), default="")
    build_status: Mapped[str] = mapped_column(String(20), default=BuildStatus.PENDING)
    status: Mapped[str] = mapped_column(String(20), default=DeployStatus.PENDING)
    health_status: Mapped[str] = mapped_column(String(20), default="Unknown")
    error_message: Mapped[str] = mapped_column(Text, default="")
    is_rollback: Mapped[bool] = mapped_column(Boolean, default=False)
    rollback_from_version: Mapped[str] = mapped_column(String(20), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    application: Mapped[Application] = relationship(back_populates="deployments")
    logs: Mapped[list["BuildLog"]] = relationship(
        back_populates="deployment", cascade="all, delete-orphan", order_by="BuildLog.id"
    )


class BuildLog(Base):
    __tablename__ = "build_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deployment_id: Mapped[int] = mapped_column(ForeignKey("deployments.id"))
    step: Mapped[str] = mapped_column(String(30), default="")  # clone / detect / build / run / health
    message: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String(10), default="info")  # info / error / success
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    deployment: Mapped[Deployment] = relationship(back_populates="logs")


class DeploymentVersion(Base):
    """A Docker image that was built AND passed its health check.

    Rollback only offers images from this table, so we never roll back to a
    broken build.
    """

    __tablename__ = "deployment_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"))
    deployment_id: Mapped[int] = mapped_column(ForeignKey("deployments.id"))
    version: Mapped[str] = mapped_column(String(20))
    image_tag: Mapped[str] = mapped_column(String(200))
    commit_id: Mapped[str] = mapped_column(String(40), default="")
    project_type: Mapped[str] = mapped_column(String(30), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    application: Mapped[Application] = relationship(back_populates="versions")
