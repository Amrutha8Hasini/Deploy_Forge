import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import APP_VERSION, app  # noqa: E402


def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_homepage_shows_name_and_version():
    response = client().get("/")
    assert response.status_code == 200
    assert b"DeployForge Sample App" in response.data
    assert f"v{APP_VERSION}".encode() in response.data


def test_health_endpoint():
    data = client().get("/health").get_json()
    assert data == {"status": "healthy", "version": APP_VERSION}


def test_info_endpoint():
    data = client().get("/api/info").get_json()
    assert data["version"] == APP_VERSION
    assert "container" in data


def test_greet_endpoint():
    assert client().get("/api/greet?name=NIE").get_json()["message"].startswith("Hello, NIE!")
    assert "World" in client().get("/api/greet").get_json()["message"]
