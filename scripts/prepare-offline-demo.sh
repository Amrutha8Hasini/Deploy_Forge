#!/usr/bin/env bash
# Backup demo for when the Expo has no internet.
#
# 1. Copies sample-app into demo-repos/deployforge-sample as a local git repo.
# 2. Pre-downloads the base images, so "docker build" works offline.
#
# Run this at home (WITH internet) the day before the Expo:
#   ./scripts/prepare-offline-demo.sh
# Then in DeployForge use repository URL  /demo-repos/deployforge-sample
# with branch  main  and an EMPTY root directory.
set -euo pipefail
cd "$(dirname "$0")/.."

TARGET=demo-repos/deployforge-sample
rm -rf "$TARGET"
mkdir -p "$TARGET"
cp -R sample-app/. "$TARGET/"
rm -rf "$TARGET/__pycache__" "$TARGET/tests/__pycache__" "$TARGET/.pytest_cache"

cd "$TARGET"
git init -q -b main
git add .
git -c user.name="DeployForge Demo" -c user.email="demo@deployforge.local" commit -q -m "Sample app v1.0.0"
cd - >/dev/null

echo "Local demo repository ready: $TARGET"
echo "Pulling base images (needs internet once)..."
docker pull python:3.12-slim
docker pull node:20-alpine
echo
echo "Done. In DeployForge, connect:  /demo-repos/deployforge-sample   (branch: main)"
echo "To make v2 offline: edit $TARGET/app.py, then run:"
echo "  cd $TARGET && git commit -am 'v2' && cd -"
