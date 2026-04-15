#!/usr/bin/env python3
"""CI/CD deployment automation: install deps, run tests, package."""

import subprocess
import sys
import os
import shutil
import tarfile
from datetime import datetime, timezone


def run(cmd, description):
    """Run a shell command, exit on failure."""
    print(f"[DEPLOY] {description}...")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"[DEPLOY] FAILED: {description}")
        sys.exit(1)
    print(f"[DEPLOY] OK: {description}")


def main():
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)

    # Install dependencies
    req_file = os.path.join(project_root, "requirements.txt")
    if not os.path.exists(req_file):
        print("[DEPLOY] ERROR: requirements.txt not found")
        sys.exit(1)
    run(
        f"{sys.executable} -m pip install -r requirements.txt --quiet",
        "Installing dependencies",
    )

    # Run tests
    run(f"{sys.executable} -m pytest tests/ -q", "Running tests")

    # Package for deployment
    dist_dir = os.path.join(project_root, "dist")
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
    os.makedirs(dist_dir)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    archive_name = f"deploy-{timestamp}.tar.gz"
    archive_path = os.path.join(dist_dir, archive_name)

    skip_dirs = {"dist", ".git", "__pycache__", ".venv", "venv", "node_modules", ".tox"}
    skip_suffixes = (".pyc", ".pyo")

    with tarfile.open(archive_path, "w:gz") as tar:
        for entry in os.scandir(project_root):
            if entry.name in skip_dirs or entry.name.startswith("."):
                continue
            if entry.is_file() and entry.name.endswith(skip_suffixes):
                continue
            tar.add(entry.path, arcname=entry.name)

    size_mb = os.path.getsize(archive_path) / (1024 * 1024)
    print(f"[DEPLOY] Package created: {archive_path} ({size_mb:.2f} MB)")
    print("[DEPLOY] Deployment pipeline complete.")


if __name__ == "__main__":
    main()