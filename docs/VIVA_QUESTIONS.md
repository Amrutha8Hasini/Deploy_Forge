# DeployForge – Viva Preparation

Answers are short on purpose: say them in your own words.

## Part A – General questions (everyone should know these)

**1. What is PaaS?**
Platform as a Service. The platform takes care of servers, runtimes and deployment; the developer only
brings the code. Examples: Heroku, Render, Railway, Vercel. (IaaS gives you a virtual machine; SaaS gives
you a finished application like Gmail.)

**2. What is DeployForge?**
A mini PaaS that runs on a laptop. It takes a GitHub repository, detects whether it is Python or Node.js,
generates a Dockerfile, builds a Docker image, runs it in a container on a free port, health-checks it, and
keeps the history so we can roll back.

**3. What problem does it solve?**
Students and small teams struggle with Dockerfiles, dependencies, CI/CD and deployment errors. DeployForge
automates those steps behind one Deploy button and shows clear logs when something fails.

**4. What is CI/CD?**
Continuous Integration: every push is automatically built and tested, so mistakes are found early.
Continuous Delivery/Deployment: after the tests pass, the software is automatically packaged (and released)
so it is always ready to deploy.

**5. What is GitHub Actions?**
GitHub's built-in automation service. Workflows are YAML files in `.github/workflows/`. Each workflow has
triggers (`on: push`), jobs that run on virtual machines called runners, and steps (commands or reusable
actions like `actions/checkout`).

**6. What does our CI pipeline do?**
Checkout → set up uv and Python → `uv sync --locked` → pytest (backend + sample app) → set up Node → type-check and build the
frontend → build Docker images → start the platform with Docker Compose → deploy the sample app through our
own API → check its `/health` → shut down.

**7. What does our CD pipeline do?**
After CI succeeds on `main`, it builds the backend and frontend images, tags them (`latest`, `sha-<commit>`,
`build-<number>`) and pushes them to GitHub Container Registry. The Deploy workflow then pulls them on our
machine and restarts the platform.

**8. What is Docker?**
A tool that packages an application with everything it needs (runtime, libraries, files) so it runs the same
way on any machine. It uses Linux features to isolate processes; it is much lighter than a virtual machine.

**9. What is a Docker image?**
A read-only template built from a Dockerfile, made of layers. Example: `deployforge/sample:v1`. Images are
stored and can be shared through registries like Docker Hub or ghcr.io.

**10. What is a container?**
A running instance of an image, with its own file system, network and processes. One image can start many
containers. Containers can be started, stopped, restarted and removed.

**11. What is a Dockerfile?**
A text file with instructions to build an image: `FROM` (base image), `WORKDIR`, `COPY`, `RUN` (run a
command while building, e.g. install packages), `EXPOSE` (document the port), `CMD` (command when the
container starts).

**12. What is Docker Compose?**
A tool to define and run several containers together using one YAML file (`docker-compose.yml`). We start
the backend and frontend, their network and volume with `docker compose up`.

**13. What is FastAPI?**
A modern Python web framework for building REST APIs. It validates input using type hints (Pydantic), is
fast, and automatically generates interactive API documentation at `/docs`.

**14. What is a REST API?**
A way for programs to talk over HTTP using URLs (resources) and methods: GET (read), POST (create/act),
PUT/PATCH (update), DELETE. Data is usually JSON. Our frontend uses it to talk to our backend.

**15. What is GitHub integration in our project?**
The user gives a repository URL, branch and (for private repos) a Personal Access Token. The backend runs
`git clone --depth 1 --branch <branch>`, reads the latest commit ID and message, and can list branches with
`git ls-remote`.

**16. What is automatic project detection?**
We look for marker files: `requirements.txt` means Python, `package.json` means Node.js, `pom.xml` means Java
(future). Then we read them to choose the start command, e.g. Flask with gunicorn → `gunicorn app:app`.

**17. What is a health check?**
An automatic test that the application really works, not just that the container is running. We call
`GET /health` (or `/`) on the new container up to 15 times, 2 seconds apart. Any answer below HTTP 500 is
healthy.

**18. What is rollback?**
Going back to an earlier working version. We keep the Docker image of every healthy version. Rollback starts
the chosen old image in a new container, health-checks it and then stops the current one.

**19. How does our deployment process work?**
Clone → detect → generate Dockerfile → `docker build` (logs saved) → save deployment → `docker run` on a free
port with limits → health check → if healthy, make it live and stop the old container → show the URL.

**20. What happens when a deployment fails?**
The step that failed is marked, the error and the app's last output are saved in the build logs, the status
becomes Failed, the new container (if any) is removed, and the previous version keeps running. The user sees
exactly why.

**21. Why SQLite?**
It is a whole database in one file, needs no server, and is supported by SQLAlchemy. Perfect for one machine.
For many users we would switch to PostgreSQL by changing `DATABASE_URL`.

**22. What is SQLAlchemy?**
An ORM (Object Relational Mapper): we write Python classes (`Application`, `Deployment`) and SQLAlchemy
creates tables and SQL queries for us.

**23. What is the Docker SDK for Python?**
The official Python library to control Docker (`import docker`). We use `client.api.build()` to build images
with streamed logs, `containers.run()` to start containers, `.stop()`, `.logs()`, `.stats()`.

**24. What is the difference between a virtual machine and a container?**
A VM runs a full operating system on virtual hardware (heavy, minutes to start). A container shares the host's
kernel and only isolates processes (light, seconds to start).

**25. What is a port mapping like `8100->8000`?**
The app listens on port 8000 inside the container. Docker forwards port 8100 on the Mac to it, so we open
`http://localhost:8100`. Each deployed app gets its own host port, so they do not clash.

**26. What is a container registry? What is ghcr.io?**
A server that stores Docker images. ghcr.io is GitHub Container Registry; our CD workflow pushes images there.

**27. What security steps did you take?**
Only the platform gets the Docker socket; apps get memory/CPU/process limits, drop all Linux capabilities,
`no-new-privileges`, a non-root user and a separate network. We only control containers with our label, validate
branch names, and hide GitHub tokens.

**28. Why did you not use Kubernetes?**
Kubernetes is for running containers on many servers. For one laptop it adds a lot of complexity. Docker and
Docker Compose are enough and easier to explain. It could be future scope.

**29. What is a self-hosted runner?**
A computer we own (our Mac) registered with GitHub that runs workflow jobs. Our Deploy workflow uses it because
our platform runs locally, not in the cloud.

**30. What is a branch? Which branches do you use?**
A separate line of development in Git. We develop on `develop`, and merge into `main` through pull requests.
CI runs on every branch; CD runs only on `main`.

**31. What is uv?**
A fast Python package and project manager from Astral. In our backend, `pyproject.toml` lists the packages, `uv.lock`
pins their exact versions, `uv sync` creates the `.venv` virtual environment and `uv run pytest` runs commands inside
it. It replaces `python -m venv` + `pip install -r requirements.txt` with one tool and reproducible installs.

## Part B – Individual questions

### Member 1 – Frontend

1. _What is React?_ A JavaScript library for building user interfaces from reusable components; it updates the page when state changes.
2. _What is TypeScript and why use it?_ JavaScript with types. Mistakes like a wrong field name are caught before running (`npm run typecheck`).
3. _What is Vite?_ A fast development server and build tool. `npm run dev` for development, `npm run build` creates optimised files in `dist/`.
4. _What is Tailwind CSS?_ A CSS framework of small utility classes (`p-4`, `rounded-xl`, `text-white`) used directly in JSX.
5. _What do `useState` and `useEffect` do?_ `useState` stores data in a component; `useEffect` runs code after rendering, e.g. loading data or starting a timer.
6. _How do live logs work?_ Polling every 1.5 s; we send `after_id` so the server returns only new lines; we stop when the deployment finishes.
7. _How does routing work without a library?_ `router.tsx` uses `history.pushState` to change the URL and an event to re-render; `App.tsx` picks the page from the path.
8. _How does the frontend reach the backend in Docker?_ nginx serves the built files and forwards `/api/` to `http://backend:8000` on the Compose network.

### Member 2 – Backend and database

1. _Explain the four tables._ applications (repos), deployments (each deploy/rollback), build_logs (log lines), deployment_versions (healthy images for rollback).
2. _What is a foreign key?_ A column pointing to another table's row, e.g. `deployments.application_id → applications.id`.
3. _What is Pydantic used for?_ Validating request JSON and shaping responses (`schemas.py`); invalid input gets HTTP 422 automatically.
4. _How does login work?_ Correct username/password → token `username:expiry:HMAC-signature`. Every request sends `Authorization: Bearer <token>`; `require_user` checks the signature and expiry.
5. _Why does Deploy return 202?_ 202 Accepted means "started, not finished". The pipeline runs as a FastAPI background task; the UI polls for progress.
6. _What is CORS?_ A browser rule blocking calls to another origin; we allow the frontend origins in development. In Docker, nginx makes it the same origin.
7. _What is dependency injection in FastAPI?_ `Depends(get_db)` gives each request a database session and closes it; `Depends(require_user)` protects routes.
8. _What happens to deployments that were running when the server stopped?_ At start-up `mark_interrupted_deployments` marks them Failed.
9. _What is uv and why did you use it instead of pip + venv?_ uv is a fast Python package and project manager. One tool creates the virtual environment, installs Python itself if needed, and writes `uv.lock` with exact versions, so every member, CI and the Docker image get identical packages.
10. _What is the difference between `pyproject.toml` and `uv.lock`?_ `pyproject.toml` says what we need (written by us); `uv.lock` records exactly which versions were chosen, including sub-dependencies (generated by uv). Both are committed.

### Member 3 – GitHub integration and detection

1. _Why `--depth 1`?_ Downloads only the latest commit, which is faster and smaller; we do not need history to build.
2. _How do you use a token with git?_ `https://x-access-token:<token>@github.com/owner/repo.git`. After cloning we reset the remote URL so the token is not stored on disk.
3. _Fine-grained vs classic token?_ Fine-grained tokens are limited to selected repositories and permissions; we only need Contents: Read-only.
4. _How do you stop command injection through the branch name?_ A regular expression allows only letters, numbers, `._/-`; names starting with `-` or containing `..` are rejected. We also call git with an argument list, not a shell string.
5. _How is a Flask app started?_ With gunicorn (production server): `gunicorn --bind 0.0.0.0:8000 --workers 2 app:app`.
6. _Why copy requirements.txt before the code in the Dockerfile?_ Docker caches layers; if only code changes, the slow `pip install` layer is reused.
7. _Why a non-root user in the container?_ If the app is hacked, the attacker has fewer permissions.
8. _What is the root directory option?_ Deploys a sub-folder of a repository (monorepo), e.g. `sample-app`; it cannot point outside the repo.

### Member 4 – Docker and CI/CD

1. _What does `docker compose up --build` do?_ Builds the images, creates the network and volume, starts the containers in the right order (frontend waits for a healthy backend).
2. _What is a multi-stage build?_ Our frontend Dockerfile builds with Node, then copies only `dist/` into a small nginx image.
3. _What is `/var/run/docker.sock`?_ The Docker Engine's API socket. Whoever has it can control Docker, so only the platform backend gets it.
4. _Explain `cap_drop: ALL` and `no-new-privileges`._ Removes special Linux powers from the app and stops it gaining more (e.g. via setuid programs).
5. _What are labels used for?_ `deployforge.managed=true` marks our containers so we never touch others; `deployforge.role=app/platform` separates them.
6. _How is CI triggered and what does `needs` do?_ `on: push`/`pull_request`; `needs` makes the docker job wait for the test and build jobs.
7. _What secrets does the pipeline need?_ None extra: the automatic `GITHUB_TOKEN` clones the repo in the E2E test and pushes to ghcr.io (`permissions: packages: write`).
8. _How are images tagged and why?_ `latest` (newest), `sha-<commit>` (exactly which code), `build-<number>` (which run). The sha tag lets us redeploy an exact version.

### Member 5 – Pipeline, monitoring, rollback, testing

1. _How is the host port chosen?_ We ask Docker which host ports all containers use and take the first free one from 8100–8199; if Docker says it is busy, we try the next.
2. _Why start the new container before stopping the old one?_ So the old version keeps working if the new one fails its health check (no downtime on failure).
3. _How is CPU % calculated?_ (container CPU time delta ÷ system CPU time delta) × number of CPUs × 100, from two samples given by `container.stats()`.
4. _Why only health-checked versions are offered for rollback?_ So we never roll back to a broken build.
5. _What if the image to roll back to was deleted?_ Rollback fails with "Image … no longer exists"; tests cover this.
6. _How do the tests work without Docker?_ `conftest.py` replaces the Docker functions and `git clone` with small fakes, so the real pipeline logic runs in seconds; the real Docker path is tested by the E2E job in CI.
7. _What does the sample app provide?_ Homepage with name/version/container ID, `/health`, `/api/info`, `/api/greet`.
8. _What is the difference between "Replaced" and "Rolled Back"?_ Replaced: a newer deploy took over. Rolled Back: a rollback to an older version took over.
