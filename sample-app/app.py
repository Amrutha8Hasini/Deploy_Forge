"""
DeployForge Sample App - a small Flask application used to demonstrate
DeployForge at the Project Expo.

Demo tip: to show a new version, change APP_VERSION (and THEME_COLOR) below,
commit, push, and click Deploy again in DeployForge.
"""

import os
import socket
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request

APP_NAME = "DeployForge Sample App"
APP_VERSION = "1.0.0"
THEME_COLOR = "#6366f1"  # indigo for v1 - try "#10b981" (green) for v2

app = Flask(__name__)
STARTED_AT = datetime.now(timezone.utc)


def app_details() -> dict:
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        # Inside Docker the hostname is the container ID, which proves
        # which container answered the request.
        "container": socket.gethostname(),
        "started_at": STARTED_AT.isoformat(),
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


@app.route("/")
def home():
    return render_template("index.html", color=THEME_COLOR, **app_details())


@app.route("/health")
def health():
    """Health-check endpoint used by DeployForge after starting the container."""
    return jsonify(status="healthy", version=APP_VERSION)


@app.route("/api/info")
def info():
    return jsonify(app_details())


@app.route("/api/greet")
def greet():
    """Simple API endpoint: /api/greet?name=NIE"""
    name = request.args.get("name", "World").strip()[:50] or "World"
    return jsonify(message=f"Hello, {name}! Greetings from version {APP_VERSION}.")


if __name__ == "__main__":
    # For running without Docker: python app.py  (then open http://localhost:8000)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
