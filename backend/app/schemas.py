"""
Request and response shapes (Pydantic models).

FastAPI uses these to validate incoming JSON and to convert database rows into
JSON. Note that `github_token` is accepted in requests but never sent back.
"""

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("*", when_used="json", check_fields=False)
    def _utc_dates(self, value):
        # SQLite forgets the timezone, so we add UTC back before sending dates
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc).isoformat()
        if isinstance(value, datetime):
            return value.isoformat()
        return value


# ----------------------------------------------------------------- auth ---
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str


# --------------------------------------------------------- repositories ---
class RepoCheckRequest(BaseModel):
    repo_url: str = Field(..., examples=["https://github.com/user/my-app"])
    branch: str = "main"
    github_token: str = ""
    root_directory: str = ""


class RepoCheckResponse(BaseModel):
    repo_owner: str
    repo_name: str
    branch: str
    commit_id: str
    commit_message: str
    project_type: str
    supported: bool
    framework: str
    message: str
    files_found: list[str]
    dockerfile: str
    internal_port: int


class BranchesRequest(BaseModel):
    repo_url: str
    github_token: str = ""


# --------------------------------------------------------- applications ---
class ApplicationCreate(BaseModel):
    repo_url: str
    branch: str = "main"
    github_token: str = ""
    root_directory: str = ""
    name: str = ""  # optional; defaults to the repository name
    project_type: str = "unknown"  # filled in by the Connect Repository page


class ApplicationOut(ORMModel):
    id: int
    name: str
    repo_url: str
    repo_owner: str
    repo_name: str
    branch: str
    root_directory: str
    project_type: str
    created_at: datetime
    current_deployment_id: int | None
    current_url: str
    has_token: bool = False
    container_status: str = "none"  # filled in from Docker
    latest_status: str = ""  # status of the newest deployment
    latest_version: str = ""


# ---------------------------------------------------------- deployments ---
class DeploymentOut(ORMModel):
    id: int
    application_id: int
    application_name: str = ""
    version: str
    commit_id: str
    commit_message: str
    project_type: str
    image_tag: str
    container_name: str
    host_port: int | None
    url: str
    build_status: str
    status: str
    health_status: str
    error_message: str
    is_rollback: bool
    rollback_from_version: str
    created_at: datetime
    finished_at: datetime | None
    is_current: bool = False


class DeploymentDetail(DeploymentOut):
    dockerfile: str


class BuildLogOut(ORMModel):
    id: int
    step: str
    message: str
    level: str
    created_at: datetime


class VersionOut(ORMModel):
    id: int
    application_id: int
    deployment_id: int
    version: str
    image_tag: str
    commit_id: str
    created_at: datetime
    image_available: bool = True
    is_current: bool = False


class RollbackRequest(BaseModel):
    version_id: int
