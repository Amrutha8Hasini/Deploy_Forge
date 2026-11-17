"""
Automatic project detection.

We look at which files exist in the repository:

    requirements.txt  -> Python
    package.json      -> Node.js
    pom.xml / build.gradle -> Java (detected, but deployment is a future enhancement)

Then we work out how to start the app and which port it listens on inside the
container. Deployed apps receive that port in the PORT environment variable.
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

PYTHON_PORT = 8000
NODE_PORT = 3000

PYTHON_ENTRY_FILES = ["app.py", "main.py", "server.py", "wsgi.py"]
NODE_ENTRY_FILES = ["server.js", "index.js", "app.js", "main.js"]


@dataclass
class DetectionResult:
    project_type: str  # "python", "node", "java" or "unknown"
    supported: bool
    framework: str = ""
    start_command: list[str] = field(default_factory=list)
    install_command: str = ""
    build_command: str = ""
    internal_port: int = 0
    files_found: list[str] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _read_requirements(path: Path) -> list[str]:
    """Return package names from requirements.txt in lower case (without versions)."""
    names = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.split("#")[0].strip()
        if not line or line.startswith("-"):
            continue
        for separator in ["==", ">=", "<=", "~=", "!=", ">", "<", "[", ";", " "]:
            line = line.split(separator)[0]
        names.append(line.strip().lower())
    return names


def _first_existing(folder: Path, candidates: list[str]) -> str | None:
    for name in candidates:
        if (folder / name).is_file():
            return name
    return None


def detect_python(folder: Path, files_found: list[str]) -> DetectionResult:
    packages = _read_requirements(folder / "requirements.txt")
    entry = _first_existing(folder, PYTHON_ENTRY_FILES)
    port = str(PYTHON_PORT)

    if "django" in packages and (folder / "manage.py").is_file():
        framework = "Django"
        command = ["python", "manage.py", "runserver", f"0.0.0.0:{port}"]
    elif "fastapi" in packages and "uvicorn" in packages and entry:
        framework = "FastAPI"
        command = ["uvicorn", f"{entry[:-3]}:app", "--host", "0.0.0.0", "--port", port]
    elif "flask" in packages and "gunicorn" in packages and entry:
        framework = "Flask"
        command = ["gunicorn", "--bind", f"0.0.0.0:{port}", "--workers", "2", f"{entry[:-3]}:app"]
    elif entry:
        framework = "Flask" if "flask" in packages else "Python"
        command = ["python", entry]
    else:
        return DetectionResult(
            project_type="python",
            supported=False,
            files_found=files_found,
            message="Python project found, but no app.py, main.py, server.py or wsgi.py to start.",
        )

    return DetectionResult(
        project_type="python",
        supported=True,
        framework=framework,
        start_command=command,
        install_command="pip install --no-cache-dir -r requirements.txt",
        internal_port=PYTHON_PORT,
        files_found=files_found,
        message=f"Detected a {framework} application (requirements.txt found).",
    )


def detect_node(folder: Path, files_found: list[str]) -> DetectionResult:
    try:
        package = json.loads((folder / "package.json").read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return DetectionResult(
            project_type="node", supported=False, files_found=files_found, message="package.json is not valid JSON."
        )

    scripts = package.get("scripts") or {}
    dependencies = {**(package.get("dependencies") or {}), **(package.get("devDependencies") or {})}
    framework = "Express" if "express" in dependencies else "Node.js"

    if "start" in scripts:
        command = ["npm", "start"]
    elif package.get("main") and (folder / package["main"]).is_file():
        command = ["node", package["main"]]
    else:
        entry = _first_existing(folder, NODE_ENTRY_FILES)
        if not entry:
            return DetectionResult(
                project_type="node",
                supported=False,
                files_found=files_found,
                message="Node.js project found, but no 'start' script or server.js / index.js to run.",
            )
        command = ["node", entry]

    has_lock_file = (folder / "package-lock.json").is_file()
    has_build = "build" in scripts
    install = "npm ci" if has_lock_file else "npm install"
    if not has_build:
        install += " --omit=dev"  # only production packages are needed

    return DetectionResult(
        project_type="node",
        supported=True,
        framework=framework,
        start_command=command,
        install_command=install,
        build_command="npm run build" if has_build else "",
        internal_port=NODE_PORT,
        files_found=files_found,
        message=f"Detected a {framework} application (package.json found).",
    )


def detect_project(folder: Path) -> DetectionResult:
    """Look at the files in `folder` and decide what kind of project it is."""
    marker_files = ["requirements.txt", "package.json", "pom.xml", "build.gradle", "Dockerfile"]
    files_found = [name for name in marker_files if (folder / name).is_file()]

    if "requirements.txt" in files_found:
        return detect_python(folder, files_found)
    if "package.json" in files_found:
        return detect_node(folder, files_found)
    if "pom.xml" in files_found or "build.gradle" in files_found:
        return DetectionResult(
            project_type="java",
            supported=False,
            files_found=files_found,
            message="Java project detected. Java deployment is planned as a future enhancement.",
        )
    return DetectionResult(
        project_type="unknown",
        supported=False,
        files_found=files_found,
        message="Could not detect the project type. Add requirements.txt (Python) or package.json (Node.js).",
    )
