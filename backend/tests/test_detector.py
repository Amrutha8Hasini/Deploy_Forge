"""Tests for automatic project detection (Module 3)."""

import json

from app.services.detector import detect_project


def test_detects_flask_with_gunicorn(tmp_path):
    (tmp_path / "requirements.txt").write_text("Flask==3.0.3\ngunicorn==22.0.0\n")
    (tmp_path / "app.py").write_text("app = None")
    result = detect_project(tmp_path)
    assert result.project_type == "python"
    assert result.supported
    assert result.framework == "Flask"
    assert result.start_command == ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "app:app"]
    assert result.internal_port == 8000


def test_detects_fastapi(tmp_path):
    (tmp_path / "requirements.txt").write_text("fastapi>=0.100\nuvicorn[standard]\n")
    (tmp_path / "main.py").write_text("app = None")
    result = detect_project(tmp_path)
    assert result.framework == "FastAPI"
    assert result.start_command[:2] == ["uvicorn", "main:app"]


def test_plain_python_uses_entry_file(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests\n")
    (tmp_path / "server.py").write_text("print('hi')")
    result = detect_project(tmp_path)
    assert result.supported
    assert result.start_command == ["python", "server.py"]


def test_python_without_entry_file_is_not_supported(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests\n")
    result = detect_project(tmp_path)
    assert result.project_type == "python"
    assert not result.supported


def test_detects_node_with_start_script(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"scripts": {"start": "node index.js"}, "dependencies": {"express": "^4"}}))
    result = detect_project(tmp_path)
    assert result.project_type == "node"
    assert result.framework == "Express"
    assert result.start_command == ["npm", "start"]
    assert result.install_command == "npm install --omit=dev"
    assert result.internal_port == 3000


def test_node_with_lock_file_uses_npm_ci(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"main": "server.js"}))
    (tmp_path / "server.js").write_text("")
    (tmp_path / "package-lock.json").write_text("{}")
    result = detect_project(tmp_path)
    assert result.start_command == ["node", "server.js"]
    assert result.install_command.startswith("npm ci")


def test_invalid_package_json(tmp_path):
    (tmp_path / "package.json").write_text("{ not json")
    assert not detect_project(tmp_path).supported


def test_java_is_detected_but_not_supported(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")
    result = detect_project(tmp_path)
    assert result.project_type == "java"
    assert not result.supported
    assert "future" in result.message.lower()


def test_unknown_project(tmp_path):
    (tmp_path / "README.md").write_text("hello")
    assert detect_project(tmp_path).project_type == "unknown"
