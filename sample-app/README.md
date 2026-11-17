# DeployForge Sample App

A small Flask app used to demonstrate DeployForge.

| Route                 | What it returns                                                                  |
| --------------------- | -------------------------------------------------------------------------------- |
| `/`                   | Homepage with app name, version and container ID                                 |
| `/health`             | `{"status": "healthy", "version": "1.0.0"}` (used by DeployForge's health check) |
| `/api/info`           | App details as JSON                                                              |
| `/api/greet?name=NIE` | A greeting message                                                               |

## Run without Docker

```bash
cd sample-app
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest
python app.py          # open http://localhost:8000
pytest                 # run the tests
```

## Deploy with DeployForge

Connect Repository → URL of this repository, branch `main` (or `develop`),
**Root directory `sample-app`**. DeployForge detects Python (Flask + gunicorn),
generates a Dockerfile and runs it.

## Show a new version during the demo

1. Edit `app.py`: change `APP_VERSION = "1.0.0"` to `"2.0.0"` and
   `THEME_COLOR` to `"#10b981"`.
2. Commit and push.
3. Click **Deploy** again → version v2 is live with a green theme.
4. Open **Deployment History** → **Rollback** to v1 → the indigo v1 page is back.
