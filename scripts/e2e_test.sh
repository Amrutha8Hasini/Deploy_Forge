#!/usr/bin/env bash
# End-to-end test: uses the RUNNING DeployForge (docker compose up) to really
# deploy the sample app, then checks that the deployed container answers.
#
# Usage:  ./scripts/e2e_test.sh <repo-url> <branch> [github-token]
# Example: ./scripts/e2e_test.sh https://github.com/Amrutha8Hasini/Deploy_Forge develop
#
# Used by the CI workflow and can also be run on your Mac.
set -euo pipefail

REPO_URL="${1:?repository URL required}"
BRANCH="${2:-main}"
TOKEN="${3:-}"
API="${API_URL:-http://localhost:8000}"
USERNAME="${ADMIN_USERNAME:-admin}"
PASSWORD="${ADMIN_PASSWORD:-admin123}"

json() { python3 -c "import sys, json; print(json.load(sys.stdin)$1)"; }

echo "==> Waiting for the backend at $API"
for i in $(seq 1 30); do
  curl -fs "$API/api/health" >/dev/null && break
  sleep 2
done
curl -fs "$API/api/health"; echo

echo "==> Logging in"
TOKEN_JSON=$(curl -fs -X POST "$API/api/auth/login" -H "Content-Type: application/json" \
  -d "{\"username\": \"$USERNAME\", \"password\": \"$PASSWORD\"}")
AUTH="Authorization: Bearer $(echo "$TOKEN_JSON" | json "['token']")"

APP_NAME="e2e-sample-$(date +%s)"
echo "==> Creating application $APP_NAME (root directory: sample-app)"
APP_JSON=$(curl -fs -X POST "$API/api/applications" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"repo_url\": \"$REPO_URL\", \"branch\": \"$BRANCH\", \"root_directory\": \"sample-app\", \"name\": \"$APP_NAME\", \"github_token\": \"$TOKEN\"}")
APP_ID=$(echo "$APP_JSON" | json "['id']")

echo "==> Deploying"
DEPLOYMENT_ID=$(curl -fs -X POST "$API/api/applications/$APP_ID/deploy" -H "$AUTH" | json "['id']")

STATUS="Pending"
for i in $(seq 1 90); do
  STATUS=$(curl -fs "$API/api/deployments/$DEPLOYMENT_ID" -H "$AUTH" | json "['status']")
  echo "    deployment #$DEPLOYMENT_ID status: $STATUS"
  [[ "$STATUS" == "Successful" || "$STATUS" == "Failed" ]] && break
  sleep 5
done

echo "==> Build logs"
curl -fs "$API/api/deployments/$DEPLOYMENT_ID/logs" -H "$AUTH" \
  | python3 -c "import sys, json; [print(f\"[{l['step']}] {l['message']}\") for l in json.load(sys.stdin)]"

if [[ "$STATUS" != "Successful" ]]; then
  echo "Deployment did not succeed (status: $STATUS)"; exit 1
fi

URL=$(curl -fs "$API/api/deployments/$DEPLOYMENT_ID" -H "$AUTH" | json "['url']")
echo "==> Calling the deployed app at $URL/health"
curl -fs "$URL/health"; echo
docker ps --filter "label=deployforge.app=$APP_NAME"

echo "==> Cleaning up"
curl -fs -X DELETE "$API/api/applications/$APP_ID" -H "$AUTH" -o /dev/null
echo "E2E test passed"
