#!/usr/bin/env bash
# Run every check on your Mac before committing:
#   ./scripts/verify.sh            (tests + frontend build + docker build)
#   ./scripts/verify.sh --e2e      (also starts compose and really deploys the sample app)
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> 1/4 Backend tests"
( cd backend
  [ -d .venv ] || python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
  .venv/bin/python -m pytest -q )

echo "==> 2/4 Sample app tests"
( cd sample-app
  [ -d .venv ] || python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt pytest
  .venv/bin/python -m pytest -q )

echo "==> 3/4 Frontend type check and build"
( cd frontend
  npm install --no-audit --no-fund
  npm run typecheck
  npm run build )

echo "==> 4/4 Docker images"
docker compose build

if [[ "${1:-}" == "--e2e" ]]; then
  echo "==> End-to-end deployment test"
  docker compose up -d
  REMOTE=$(git remote get-url origin | sed 's/\.git$//')
  BRANCH=$(git rev-parse --abbrev-ref HEAD)
  echo "NOTE: this deploys sample-app from $REMOTE ($BRANCH) - push your changes first."
  ./scripts/e2e_test.sh "$REMOTE" "$BRANCH" "${GITHUB_TOKEN:-}"
fi

echo "All checks passed."
