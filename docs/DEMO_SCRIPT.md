# DeployForge – Project Expo Demonstration (8–10 minutes)

## Before the examiner arrives (setup checklist)

Do this 15 minutes before. **Terminal 1** and **Terminal 2**, folder `Deploy_Forge`.

1. Docker Desktop is running ("Engine running").
2. Start the platform: `docker compose up -d --build` → wait until `docker compose ps` shows both containers `Up` (backend `healthy`).
3. Open in the browser (tabs in this order):
   1. <http://localhost:3000> (logged in)
   2. GitHub repository → **Actions** tab, with the latest green CI run open
   3. <http://localhost:8000/docs>
4. Clean slate (optional, for a fresh dashboard): `docker compose down -v && docker compose up -d`.
5. In `sample-app/app.py`, `APP_VERSION = "1.0.0"` is pushed. Have a **second commit ready** on a
   branch or stash: `APP_VERSION = "2.0.0"`, `THEME_COLOR = "#10b981"`. Simplest: prepare it in
   the editor, but do not save until step 8.
6. Do one full rehearsal earlier the same day so the base image `python:3.12-slim` is cached
   (the first build downloads ~50 MB).
7. Terminal font size large (⌘ +), browser zoom 110%.

## The demo

| Time       | Who          | Do                                                                                                                                                    | Say                                                                                                                                                                                                                                                                                                                                                               |
| ---------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0:00–1:00  | **Member 1** | Show the title slide, then the dashboard                                                                                                              | "Deploying an app normally means writing a Dockerfile, building images and running containers by hand. DeployForge is a mini Platform-as-a-Service: you give it a GitHub repository and it does all of that with one click, on Docker, with a real CI/CD pipeline."                                                                                               |
| 1:00–1:45  | **Member 1** | Walk through the dashboard cards, chart, sidebar pages                                                                                                | "This is built with React, TypeScript, Vite and Tailwind. The numbers come from our FastAPI backend and refresh every five seconds."                                                                                                                                                                                                                              |
| 1:45–3:00  | **Member 3** | **Connect Repository**: paste the repo URL, click **Load** (branches appear), branch `develop`, root directory `sample-app`, click **Fetch & detect** | "The backend runs `git clone --depth 1` on the branch. It found `requirements.txt`, so it detected **Python**, and because Flask and gunicorn are listed, it chose `gunicorn app:app`. Here is the Dockerfile it generated: dependencies first for caching, then the code, a non-root user, port 8000. For private repositories we paste a read-only token here." |
| 3:00–3:15  | **Member 3** | Click **Save application**                                                                                                                            | "The application is saved in our SQLite database."                                                                                                                                                                                                                                                                                                                |
| 3:15–4:45  | **Member 5** | Click **Deploy**, Build Logs page opens                                                                                                               | "Deploy returns immediately and the pipeline runs in the background. You can see every step: clone, detect, Dockerfile, and now the real Docker build output, line by line. Next it starts a container on a free port, 8100, and does a health check on `/health`. Only when that passes is the version marked successful."                                       |
| 4:45–5:30  | **Member 4** | **Terminal 2**: `docker images \| grep deployforge` then `docker ps --filter label=deployforge.role=app`                                              | "Here is the image `deployforge/<app>:v1` that was just built, and the running container with port mapping 8100 → 8000. The platform runs in its own containers, `deployforge-backend` and `deployforge-frontend`, so they are clearly separate."                                                                                                                 |
| 5:30–6:00  | **Member 5** | Click **Open application**                                                                                                                            | "This is the sample app inside the container. The container ID on the page matches `docker ps`."                                                                                                                                                                                                                                                                  |
| 6:00–7:00  | **Member 5** | Save the v2 change, `git commit -am "feat(sample-app): v2.0.0" && git push`, then **Projects → Deploy**                                               | "We changed the version and colour and pushed. Deploying again builds v2 on a new port; only after v2 is healthy is v1's container stopped." Open v2 (green).                                                                                                                                                                                                     |
| 7:00–8:00  | **Member 5** | **Deployment History** → select app → **Roll back to v1** → Open application                                                                          | "History shows ID, version, commit, time, build and deployment status. Rollback does not just change a label: it starts the stored v1 image in a new container. No clone, no build, so it takes a few seconds. v2 is now marked Rolled Back."                                                                                                                     |
| 8:00–8:30  | **Member 2** | **Monitoring** page, click **Logs**, then **Stop** and **Start**                                                                                      | "Monitoring reads real CPU and memory numbers from the Docker SDK, health from an HTTP check, and these buttons stop, start and restart the container." Optionally show `docker stats --no-stream` matching.                                                                                                                                                      |
| 8:30–9:30  | **Member 4** | Switch to the **GitHub Actions** tab, open the green CI run                                                                                           | "On every push, CI installs dependencies, runs pytest, builds the frontend, builds the Docker images, starts the whole platform with Docker Compose and deploys this same sample app through our API, then calls its health endpoint. After CI passes on main, CD tags the images and publishes them to GitHub Container Registry."                               |
| 9:30–10:00 | **Member 2** | Show `/docs` briefly; conclude                                                                                                                        | "The backend exposes a documented REST API. In short: GitHub → automatic detection → Docker image → container → health check → history and rollback, with CI/CD. Thank you."                                                                                                                                                                                      |

If time is short, skip the Monitoring stop/start and the `/docs` page.

## If something goes wrong during the demo

| Problem                                | Quick action                                                                                                       |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Build is slow (downloading base image) | Keep talking through the logs; that is real `docker build`. Rehearse earlier to cache the image.                   |
| Health check fails                     | Show the error and the "Last application output" lines — explain the old version keeps running. This is a feature. |
| Browser shows old page                 | Hard refresh ⌘ + Shift + R                                                                                         |
| Port 3000/8000 busy                    | `docker compose down`, close other servers, `docker compose up -d`                                                 |

## Backup demonstration (no internet at the Expo)

Without internet, cloning from GitHub, `pip install` inside the build, and the
Actions tab do not work. Prepare this **the day before, at home with internet**:

```bash
cd Deploy_Forge
./scripts/prepare-offline-demo.sh      # local git copy of sample-app + pulls python:3.12-slim
docker compose up -d --build           # builds the platform images while online
```

Then do one complete deploy of the local repo at home so the Python packages
layer is cached in Docker: in DeployForge connect repository URL
`/demo-repos/deployforge-sample`, branch `main`, **empty** root directory → Deploy.

**At the Expo (offline):**

1. `docker compose up -d` (no `--build`, images already exist).
2. Use the app connected to `/demo-repos/deployforge-sample`. Deploy works because the base image
   and the dependency layer are cached (requirements.txt is unchanged).
3. For v2: edit `demo-repos/deployforge-sample/app.py`, then
   `cd demo-repos/deployforge-sample && git commit -am "v2" && cd ../..` and click Deploy.
4. Rollback and monitoring work fully offline.
5. For CI/CD, show **screenshots of a green Actions run** taken beforehand, plus the workflow files
   in VS Code, and the result of `./scripts/verify.sh` run beforehand.

Take these screenshots the day before as a last-resort backup: dashboard, build logs of a successful
deploy, deployment history with a rollback, monitoring page, green CI run, CD run, Packages page.
