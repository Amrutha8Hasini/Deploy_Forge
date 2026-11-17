"""
Shared test setup.

* Every test run uses a fresh temporary folder for the SQLite database.
* API tests replace Docker and git with small fakes, so the tests run in a few
  seconds on any machine (including GitHub Actions) without Docker Desktop.
  The real Docker code is exercised in the CI "docker" job and in the demo.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Must be set BEFORE the app is imported, because config.py reads them once.
_TEST_DATA_DIR = tempfile.mkdtemp(prefix="deployforge-test-")
os.environ["DATA_DIR"] = _TEST_DATA_DIR
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "test-password"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["HEALTH_CHECK_INTERVAL"] = "0"

# Make "import app" work when pytest is run from the backend folder
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ------------------------------------------------------------ fakes ---


class FakeContainer:
    def __init__(self, name, image, labels):
        self.id = f"id-{name}"
        self.short_id = self.id[:12]
        self.name = name
        self.image = image
        self.labels = labels
        self.status = "running"
        self.attrs = {"Created": "2026-01-01T00:00:00Z"}

    def reload(self):
        pass

    def logs(self, tail=100, timestamps=False):
        return b"fake application output\n"

    def remove(self, force=False):
        FakeDocker.instance.containers.pop(self.name, None)


class FakeDocker:
    """Keeps 'images' and 'containers' in dictionaries instead of Docker."""

    instance = None

    def __init__(self):
        self.images: set[str] = set()
        self.containers: dict[str, FakeContainer] = {}
        self.healthy = True
        self.build_should_fail = False
        FakeDocker.instance = self

    # --- functions that replace app.services.docker_service ---
    def build_image(self, context_dir, dockerfile_name, tag, labels, on_log):
        assert (Path(context_dir) / dockerfile_name).is_file(), "Dockerfile was not written"
        on_log("Step 1/8 : FROM python:3.12-slim")
        if self.build_should_fail:
            from app.services.docker_service import DockerBuildError

            raise DockerBuildError("pip install failed")
        on_log("Successfully built")
        self.images.add(tag)

    def run_app_container(self, image_tag, container_name, host_port, internal_port, labels):
        assert image_tag in self.images, f"image {image_tag} was never built"
        container = FakeContainer(container_name, image_tag, {"deployforge.managed": "true", "deployforge.role": "app", **labels})
        self.containers[container_name] = container
        return container

    def remove_container_if_exists(self, name):
        self.containers.pop(name, None)

    def used_host_ports(self):
        return {int(c.labels["deployforge.host_port"]) for c in self.containers.values()}

    def image_exists(self, tag):
        return tag in self.images

    def remove_image(self, tag):
        self.images.discard(tag)

    def list_app_containers(self):
        return list(self.containers.values())


@pytest.fixture
def fake_docker(monkeypatch, tmp_path):
    from app.services import deployment_service, docker_service, health_checker
    from app.services.github_service import CloneResult

    fake = FakeDocker()
    for name in ["build_image", "run_app_container", "remove_container_if_exists", "used_host_ports",
                 "image_exists", "remove_image", "list_app_containers"]:
        monkeypatch.setattr(docker_service, name, getattr(fake, name))

    # Fake "git clone": create a small Flask project on disk
    def fake_clone(repo_url, branch, destination, token=""):
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "requirements.txt").write_text("flask==3.0.3\ngunicorn==22.0.0\n")
        (destination / "app.py").write_text("from flask import Flask\napp = Flask(__name__)\n")
        return CloneResult(path=destination, commit_id="a" * 40, commit_message="Test commit")

    monkeypatch.setattr(deployment_service, "clone_repository", fake_clone)
    monkeypatch.setattr(
        health_checker, "wait_until_healthy", lambda *args, **kwargs: FakeDocker.instance.healthy
    )
    return fake


@pytest.fixture
def client(fake_docker):
    from fastapi.testclient import TestClient

    from app.database import Base, engine
    from app.main import app

    # Start every test with empty tables
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client):
    response = client.post("/api/auth/login", json={"username": "admin", "password": "test-password"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}
