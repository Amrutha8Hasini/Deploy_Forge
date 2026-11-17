# DeployForge – Team Division

Each member owns one area end to end: the code, the tests for it, a part of
the demo, two slides of the presentation, and the viva questions about it.
Everybody should still be able to explain the overall flow (see
[deployment-flow.png](diagrams/deployment-flow.png)).

| Member | Area                                                        | Main files                                                                                                         | Demo part                                           | Slides |
| ------ | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------- | ------ |
| 1      | Frontend & dashboard                                        | `frontend/`                                                                                                        | Dashboard, Connect Repository UI                    | 1–3    |
| 2      | Backend & database                                          | `backend/app/main.py`, `models.py`, `database.py`, `schemas.py`, `auth.py`, `routers/`                             | Login, API docs, database                           | 4–6    |
| 3      | GitHub integration & detection                              | `github_service.py`, `detector.py`, `dockerfile_generator.py`                                                      | Fetch & detect, Dockerfile                          | 7–9    |
| 4      | Docker, Compose, CI/CD                                      | `docker_service.py`, Dockerfiles, `docker-compose*.yml`, `.github/workflows/`, `scripts/`                          | `docker compose`, images/containers, GitHub Actions | 10–12  |
| 5      | Deployment pipeline, history, monitoring, rollback, testing | `deployment_service.py`, `health_checker.py`, `stats.py`, `routers/monitoring.py`, `backend/tests/`, `sample-app/` | Deploy, history, rollback, monitoring               | 13–15  |

---

## Member 1 – Frontend development and dashboard

**Modules:** 1 (Dashboard) and the user interface of all 9 pages.

**Files:**

- `frontend/src/App.tsx` – chooses the page for the current URL; sends logged-out users to /login
- `frontend/src/router.tsx` – a 40-line router using the browser History API (no library)
- `frontend/src/api.ts` – every backend call, TypeScript types, token storage
- `frontend/src/components/Layout.tsx` – sidebar navigation, mobile menu
- `frontend/src/components/ui.tsx` – status badges, page header, progress bar, `usePolling` hook
- `frontend/src/components/Icons.tsx` – SVG icons
- `frontend/src/pages/*.tsx` – Login, Dashboard, Projects, ConnectRepository, CreateDeployment, BuildLogs, DeploymentHistory, Monitoring, Settings
- `frontend/src/index.css` – Tailwind theme (dark, blue/violet)
- `frontend/vite.config.ts`, `package.json`, `tsconfig.json`

**Exact contribution:**

- Designed the dark developer-dashboard look (cards, badges, sidebar) inspired by Vercel/Render.
- Built the dashboard: 4 stat cards, a 7-day bar chart drawn with plain `div`s, app status list and recent activity, refreshed every 5 s.
- Built the live Build Logs page: polls `/api/deployments/{id}/logs?after_id=N` every 1.5 s and only fetches new lines; shows a 7-step pipeline progress bar.
- Built forms for Connect Repository and Create Deployment with error messages from the API.

**Commands:**

```bash
cd frontend
npm install          # install React, Vite, Tailwind
npm run dev          # development server on http://localhost:5173
npm run typecheck    # TypeScript checks
npm run build        # production build into dist/
```

**Explain to the examiner:**

- React components and state (`useState`, `useEffect`); why the page re-renders when data changes.
- How the frontend talks to the backend: `fetch('/api/...')` with a `Bearer` token; Vite proxy in development, nginx proxy in Docker.
- What "polling" is and why we used it instead of WebSockets (simpler, enough for a demo).
- Tailwind: utility classes like `rounded-xl border bg-surface`; theme colours defined once in `index.css`.

---

## Member 2 – Backend development and database

**Modules:** REST API, database, login.

**Files:**

- `backend/pyproject.toml`, `backend/uv.lock`, `backend/.python-version` – Python dependencies managed with uv
- `backend/app/main.py` – creates the FastAPI app, CORS, registers routers, creates tables at start-up
- `backend/app/config.py` – all settings from environment variables with defaults
- `backend/app/database.py` – SQLAlchemy engine for SQLite, `SessionLocal`, `get_db` dependency
- `backend/app/models.py` – the 4 tables and the status values
- `backend/app/schemas.py` – Pydantic request/response models (token is accepted but never returned)
- `backend/app/auth.py` – HMAC-signed login token, `require_user` dependency
- `backend/app/routers/auth.py`, `applications.py`, `deployments.py`, `containers.py`
- `backend/tests/test_auth.py`, `backend/tests/test_api.py` (shared with Member 5)

**Exact contribution:**

- Designed the database schema (applications → deployments → build_logs; deployment_versions for rollback).
- Wrote all REST endpoints, input validation and clear error codes (400, 401, 404, 409, 503).
- Implemented the simple login: token = `username:expiry:signature`, checked on every request.
- Background tasks: the Deploy endpoint returns immediately (HTTP 202) and the pipeline runs in the background.

**Commands:**

```bash
cd backend
uv sync                                        # create .venv and install from uv.lock
uv run uvicorn app.main:app --reload --port 8000   # API on :8000, docs on /docs
uv run pytest tests/test_api.py tests/test_auth.py -v
uv add <package>                               # add a dependency (updates pyproject.toml + uv.lock)
sqlite3 data/deployforge.db ".tables"          # show the tables
sqlite3 data/deployforge.db "select id, version, status from deployments;"
```

**Explain to the examiner:**

- What a REST API is (GET to read, POST to create/act, DELETE to remove) and show `/docs` (Swagger UI generated by FastAPI).
- The 4 tables and their relationships (one application has many deployments; one deployment has many log lines).
- Why SQLite: a single file, no server, perfect for a local demo.
- How login works and why the GitHub token is never sent back to the browser.
- How Python dependencies are managed with uv: `pyproject.toml` lists what we need, `uv.lock` pins exact versions, `uv sync` builds `.venv`, `uv run` runs inside it.

---

## Member 3 – GitHub integration and automatic project detection

**Modules:** 2 (GitHub), 3 (detection), 4 (Dockerfile generation).

**Files:**

- `backend/app/services/github_service.py` – URL parsing, branch validation, `git clone --depth 1`, `git ls-remote` for branches, token in the clone URL, token hidden from errors
- `backend/app/services/detector.py` – Python/Node/Java detection, framework and start command
- `backend/app/services/dockerfile_generator.py` – Python and Node.js Dockerfile templates
- `backend/app/routers/applications.py` – `/api/repositories/check` and `/branches` endpoints
- `backend/tests/test_github_service.py`, `test_detector.py`, `test_dockerfile_generator.py`

**Exact contribution:**

- Detection rules: `requirements.txt` → Python (Flask+gunicorn → `gunicorn app:app`, FastAPI+uvicorn → `uvicorn main:app`, Django → `manage.py runserver`, else `python app.py`); `package.json` → Node.js (`npm start`, or `node <main>`); `pom.xml`/`build.gradle` → Java, marked as future enhancement.
- Dockerfile templates that cache dependencies, run as a non-root user and use the `PORT` variable.
- Root directory support for monorepos (our sample app lives in `sample-app/`).
- Security: branch names are checked with a regular expression, root directory cannot escape the repo, tokens are removed from logs and `.git/config`.

**Commands:**

```bash
cd backend
uv run pytest tests/test_detector.py tests/test_dockerfile_generator.py tests/test_github_service.py -v
uv run python -c "from pathlib import Path; from app.services.detector import detect_project; print(detect_project(Path('../sample-app')))"
git ls-remote --heads https://github.com/Amrutha8Hasini/Deploy_Forge
```

**Explain to the examiner:**

- What `git clone --depth 1 --branch X` does (only the latest commit → fast).
- What a Personal Access Token is and why fine-grained, read-only "Contents" permission is enough.
- How detection works (show `detector.py`) and show the generated Dockerfile line by line.
- Why we write `Dockerfile.deployforge` instead of overwriting the project's own Dockerfile.

---

## Member 4 – Docker, Docker Compose and GitHub Actions CI/CD

**Modules:** 6 (container management) and the whole DevOps setup.

**Files:**

- `backend/app/services/docker_service.py` – Docker SDK: build with streamed logs, run with limits, start/stop/restart/logs, list containers, labels
- `backend/app/routers/containers.py` – container endpoints
- `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf`, both `.dockerignore` files
- `docker-compose.yml`, `docker-compose.prod.yml`, `.env.example`
- `.github/workflows/ci.yml`, `cd.yml`, `deploy.yml`
- `scripts/e2e_test.sh`, `scripts/verify.sh`, `scripts/prepare-offline-demo.sh`

**Exact contribution:**

- Containerised the platform: backend (Python + git), frontend (multi-stage Node build → nginx).
- Compose file with two separate networks, a data volume, health check, and the Docker socket only for the backend.
- Security options for deployed apps: memory/CPU/PID limits, `cap_drop: ALL`, `no-new-privileges`, labels so only DeployForge containers are touched.
- CI: tests → frontend build → Docker build → compose up → **real end-to-end deployment of the sample app** in GitHub Actions.
- CD: multi-architecture images tagged `latest` / `sha-xxxx` / `build-N`, pushed to GitHub Container Registry.
- Deploy workflow for a self-hosted runner.

**Commands:**

```bash
docker compose build
docker compose up -d
docker compose ps
docker images | grep deployforge
docker ps --filter label=deployforge.role=app
docker compose logs -f backend
docker compose down
./scripts/verify.sh
```

**Explain to the examiner:**

- Image vs container vs Dockerfile vs Compose (see viva answers).
- Walk through `ci.yml` job by job, open the green run in the Actions tab and the E2E step logs.
- Why the Docker socket is powerful and why only the platform gets it.
- How the CD workflow tags images and where they appear (repo → Packages).

---

## Member 5 – Deployment history, monitoring, health checks, rollback and testing

**Modules:** 5 (build pipeline), 7 (deployment), 8 (history), 9 (rollback), 10 (monitoring), testing, sample app.

**Files:**

- `backend/app/services/deployment_service.py` – the 9-step pipeline, version numbering, port selection, switch-over, rollback
- `backend/app/services/health_checker.py` – `/health` then `/`, retries
- `backend/app/services/stats.py` – CPU % and memory formula (same as `docker stats`)
- `backend/app/routers/monitoring.py` – dashboard numbers, monitoring, settings
- `backend/tests/conftest.py` (fake Docker for tests), `test_api.py`, `test_stats.py`
- `sample-app/` – the Flask demo app and its tests

**Exact contribution:**

- Safe switch-over: the new container must pass the health check before the old one is stopped; on failure the new one is removed and the old one keeps serving.
- Version numbering v1, v2…; only healthy builds are saved in `deployment_versions`.
- Rollback that really starts the old image in a new container and marks the replaced deployment "Rolled Back".
- Monitoring with real Docker statistics and live health checks, collected in parallel.
- Test suite with a fake Docker so tests run anywhere in seconds; covers success, build failure, health failure, rollback, missing image.

**Commands:**

```bash
cd backend && uv run pytest -v
cd ../sample-app && uv run --no-project --with-requirements requirements.txt --with pytest pytest -v
docker stats --no-stream
curl http://localhost:8100/health
docker images deployforge/*
```

**Explain to the examiner:**

- The deployment flow diagram, step by step, including what happens when it fails.
- Why a health check is needed (a container can be "running" while the app inside has crashed).
- How rollback works and why it is fast (no clone, no build: the image already exists).
- How CPU % is calculated and what the tests check.
