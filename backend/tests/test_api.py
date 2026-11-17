"""
API tests: login, applications, the full deploy pipeline, history and rollback.

Docker and git are replaced by fakes (see conftest.py), but everything else is
the real code: FastAPI routes, SQLAlchemy models, detection, Dockerfile
generation and the deployment/rollback logic.
"""

REPO = "https://github.com/demo-user/deployforge-sample"


def create_app(client, headers, **extra):
    body = {"repo_url": REPO, "branch": "main", **extra}
    response = client.post("/api/applications", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def deploy(client, headers, app_id):
    response = client.post(f"/api/applications/{app_id}/deploy", headers=headers)
    assert response.status_code == 202, response.text
    # TestClient runs background tasks before returning, so it is finished now
    return client.get(f"/api/deployments/{response.json()['id']}", headers=headers).json()


# ------------------------------------------------------------------ auth ---


def test_health_endpoint_needs_no_login(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_login_with_wrong_password(client):
    response = client.post("/api/auth/login", json={"username": "admin", "password": "nope"})
    assert response.status_code == 401


def test_protected_endpoint_without_token(client):
    assert client.get("/api/applications").status_code == 401
    assert client.get("/api/applications", headers={"Authorization": "Bearer fake"}).status_code == 401


def test_token_check(client, auth_headers):
    assert client.get("/api/auth/me", headers=auth_headers).json() == {"username": "admin"}


# ----------------------------------------------------------- applications ---


def test_create_and_list_application(client, auth_headers):
    app = create_app(client, auth_headers, github_token="ghp_secret")
    assert app["name"] == "deployforge-sample"
    assert app["repo_owner"] == "demo-user"
    assert app["has_token"] is True
    assert "github_token" not in app  # the token is never sent back

    apps = client.get("/api/applications", headers=auth_headers).json()
    assert [a["name"] for a in apps] == ["deployforge-sample"]


def test_invalid_repository_url(client, auth_headers):
    response = client.post("/api/applications", json={"repo_url": "not-a-url"}, headers=auth_headers)
    assert response.status_code == 400


def test_duplicate_application_name(client, auth_headers):
    create_app(client, auth_headers)
    response = client.post("/api/applications", json={"repo_url": REPO}, headers=auth_headers)
    assert response.status_code == 409


# ------------------------------------------------------------ deployment ---


def test_successful_deployment(client, auth_headers, fake_docker):
    app = create_app(client, auth_headers)
    deployment = deploy(client, auth_headers, app["id"])

    assert deployment["status"] == "Successful"
    assert deployment["build_status"] == "Successful"
    assert deployment["health_status"] == "Healthy"
    assert deployment["version"] == "v1"
    assert deployment["project_type"] == "python"
    assert deployment["image_tag"] == "deployforge/deployforge-sample:v1"
    assert deployment["url"] == "http://localhost:8100"
    assert "FROM python:3.12-slim" in deployment["dockerfile"]
    assert deployment["is_current"] is True
    assert len(fake_docker.containers) == 1

    logs = client.get(f"/api/deployments/{deployment['id']}/logs", headers=auth_headers).json()
    steps = [line["step"] for line in logs]
    for step in ["clone", "detect", "dockerfile", "build", "run", "health", "done"]:
        assert step in steps

    # Polling with after_id only returns newer lines
    newer = client.get(f"/api/deployments/{deployment['id']}/logs?after_id={logs[-2]['id']}", headers=auth_headers)
    assert len(newer.json()) == 1


def test_second_deployment_replaces_first(client, auth_headers, fake_docker):
    app = create_app(client, auth_headers)
    first = deploy(client, auth_headers, app["id"])
    second = deploy(client, auth_headers, app["id"])

    assert second["version"] == "v2"
    assert second["url"] != first["url"]  # new container gets a new port
    assert list(fake_docker.containers) == [second["container_name"]]  # old container removed

    history = client.get(f"/api/deployments?application_id={app['id']}", headers=auth_headers).json()
    assert [d["status"] for d in history] == ["Successful", "Replaced"]


def test_failed_build_is_recorded(client, auth_headers, fake_docker):
    app = create_app(client, auth_headers)
    fake_docker.build_should_fail = True
    deployment = deploy(client, auth_headers, app["id"])

    assert deployment["status"] == "Failed"
    assert deployment["build_status"] == "Failed"
    assert "pip install failed" in deployment["error_message"]
    assert fake_docker.containers == {}


def test_failed_health_check_keeps_previous_version(client, auth_headers, fake_docker):
    app = create_app(client, auth_headers)
    first = deploy(client, auth_headers, app["id"])

    fake_docker.healthy = False
    second = deploy(client, auth_headers, app["id"])

    assert second["status"] == "Failed"
    assert second["build_status"] == "Successful"  # the image built, but the app did not start
    assert second["health_status"] == "Unhealthy"
    # The first version is still running and still the live one
    assert list(fake_docker.containers) == [first["container_name"]]
    current = client.get(f"/api/applications/{app['id']}", headers=auth_headers).json()
    assert current["current_deployment_id"] == first["id"]


# --------------------------------------------------------------- rollback ---


def test_rollback_starts_previous_image(client, auth_headers, fake_docker):
    app = create_app(client, auth_headers)
    deploy(client, auth_headers, app["id"])
    v2 = deploy(client, auth_headers, app["id"])

    versions = client.get(f"/api/applications/{app['id']}/versions", headers=auth_headers).json()
    assert [v["version"] for v in versions] == ["v2", "v1"]
    assert versions[0]["is_current"] is True
    v1_version_id = versions[1]["id"]

    response = client.post(
        f"/api/applications/{app['id']}/rollback", json={"version_id": v1_version_id}, headers=auth_headers
    )
    assert response.status_code == 202, response.text
    rollback = client.get(f"/api/deployments/{response.json()['id']}", headers=auth_headers).json()

    assert rollback["status"] == "Successful"
    assert rollback["is_rollback"] is True
    assert rollback["version"] == "v1"
    assert rollback["rollback_from_version"] == "v2"
    assert rollback["image_tag"] == "deployforge/deployforge-sample:v1"
    # A real container was started from the old image, and v2's container is gone
    assert list(fake_docker.containers) == [rollback["container_name"]]
    assert fake_docker.containers[rollback["container_name"]].image == "deployforge/deployforge-sample:v1"

    old_v2 = client.get(f"/api/deployments/{v2['id']}", headers=auth_headers).json()
    assert old_v2["status"] == "Rolled Back"


def test_cannot_rollback_to_live_version(client, auth_headers):
    app = create_app(client, auth_headers)
    deploy(client, auth_headers, app["id"])
    version_id = client.get(f"/api/applications/{app['id']}/versions", headers=auth_headers).json()[0]["id"]
    response = client.post(f"/api/applications/{app['id']}/rollback", json={"version_id": version_id}, headers=auth_headers)
    assert response.status_code == 400


def test_rollback_fails_when_image_was_deleted(client, auth_headers, fake_docker):
    app = create_app(client, auth_headers)
    deploy(client, auth_headers, app["id"])
    deploy(client, auth_headers, app["id"])
    versions = client.get(f"/api/applications/{app['id']}/versions", headers=auth_headers).json()
    fake_docker.images.discard("deployforge/deployforge-sample:v1")

    response = client.post(f"/api/applications/{app['id']}/rollback", json={"version_id": versions[1]["id"]}, headers=auth_headers)
    rollback = client.get(f"/api/deployments/{response.json()['id']}", headers=auth_headers).json()
    assert rollback["status"] == "Failed"
    assert "no longer exists" in rollback["error_message"]


# -------------------------------------------------------------- dashboard ---


def test_dashboard_counts(client, auth_headers, fake_docker):
    app = create_app(client, auth_headers)
    deploy(client, auth_headers, app["id"])
    fake_docker.build_should_fail = True
    deploy(client, auth_headers, app["id"])

    data = client.get("/api/dashboard", headers=auth_headers).json()
    assert data["total_applications"] == 1
    assert data["successful_deployments"] == 1
    assert data["failed_deployments"] == 1
    assert data["running_containers"] == 1
    assert len(data["deployments_per_day"]) == 7
    assert len(data["recent_deployments"]) == 2


def test_delete_application_removes_containers(client, auth_headers, fake_docker):
    app = create_app(client, auth_headers)
    deploy(client, auth_headers, app["id"])
    assert client.delete(f"/api/applications/{app['id']}", headers=auth_headers).status_code == 204
    assert fake_docker.containers == {}
    assert client.get("/api/applications", headers=auth_headers).json() == []
