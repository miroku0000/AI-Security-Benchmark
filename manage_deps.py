#!/usr/bin/env python3
"""
Dependency lock file manager for AI Security Benchmark.

Generates and updates pinned requirements files with hashes for reproducible
installs across development and production environments.

Usage:
    python manage_deps.py lock          # Generate requirements-lock.txt from requirements.txt
    python manage_deps.py update        # Update all deps to latest compatible versions and re-lock
    python manage_deps.py update PKG    # Update a single package and re-lock
    python manage_deps.py verify        # Verify installed packages match the lock file
    python manage_deps.py install       # Install from the lock file (pip install -r requirements-lock.txt)
    python manage_deps.py diff          # Show differences between lock file and installed packages
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
REQUIREMENTS_IN = PROJECT_ROOT / "requirements.txt"
REQUIREMENTS_LOCK = PROJECT_ROOT / "requirements-lock.txt"


def run(cmd: list[str], check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, capture_output=capture, text=True)


def ensure_pip_tools():
    """Install pip-tools if not already available."""
    try:
        import piptools  # noqa: F401
    except ImportError:
        print("Installing pip-tools...")
        run([sys.executable, "-m", "pip", "install", "pip-tools"])


def cmd_lock(args):
    """Compile requirements.txt into a fully pinned lock file with hashes."""
    ensure_pip_tools()

    if not REQUIREMENTS_IN.exists():
        print(f"Error: {REQUIREMENTS_IN} not found.")
        sys.exit(1)

    cmd = [
        sys.executable, "-m", "piptools", "compile",
        "--generate-hashes",
        "--output-file", str(REQUIREMENTS_LOCK),
        "--strip-extras",
        "--allow-unsafe",
        "--resolver=backtracking",
        str(REQUIREMENTS_IN),
    ]

    if args.upgrade:
        cmd.append("--upgrade")

    print(f"Locking dependencies from {REQUIREMENTS_IN.name} -> {REQUIREMENTS_LOCK.name}")
    result = run(cmd, check=False, capture=False)
    if result.returncode != 0:
        print("\nLock failed. Common causes:")
        print("  - A package in requirements.txt doesn't exist on PyPI")
        print("  - Conflicting version constraints between packages")
        print("  - Private/internal packages need --extra-index-url")
        print("\nTo add a private index, set PIP_EXTRA_INDEX_URL or use:")
        print("  python manage_deps.py lock --pip-args '--extra-index-url https://...'")
        sys.exit(1)

    print(f"\nLock file written: {REQUIREMENTS_LOCK}")
    print("Commit this file to version control for reproducible installs.")


def cmd_update(args):
    """Update dependencies and regenerate the lock file."""
    ensure_pip_tools()

    if not REQUIREMENTS_IN.exists():
        print(f"Error: {REQUIREMENTS_IN} not found.")
        sys.exit(1)

    cmd = [
        sys.executable, "-m", "piptools", "compile",
        "--generate-hashes",
        "--output-file", str(REQUIREMENTS_LOCK),
        "--strip-extras",
        "--allow-unsafe",
        "--resolver=backtracking",
        str(REQUIREMENTS_IN),
    ]

    if args.package:
        for pkg in args.package:
            cmd.extend(["--upgrade-package", pkg])
        print(f"Updating {', '.join(args.package)} and re-locking...")
    else:
        cmd.append("--upgrade")
        print("Updating all dependencies to latest compatible versions...")

    result = run(cmd, check=False, capture=False)
    if result.returncode != 0:
        print("\nUpdate failed. See output above for details.")
        sys.exit(1)

    print(f"\nLock file updated: {REQUIREMENTS_LOCK}")


def cmd_verify(args):
    """Verify installed packages match the lock file."""
    if not REQUIREMENTS_LOCK.exists():
        print(f"Error: {REQUIREMENTS_LOCK} not found. Run 'lock' first.")
        sys.exit(1)

    # Get installed packages
    result = run([sys.executable, "-m", "pip", "list", "--format=json"])
    installed = {
        pkg["name"].lower(): pkg["version"]
        for pkg in json.loads(result.stdout)
    }

    # Parse lock file
    locked = _parse_lock_file()

    mismatches = []
    missing = []

    for name, version in sorted(locked.items()):
        inst_version = installed.get(name)
        if inst_version is None:
            missing.append((name, version))
        elif inst_version != version:
            mismatches.append((name, version, inst_version))

    if not mismatches and not missing:
        print("All installed packages match the lock file.")
        return

    if missing:
        print(f"\n{len(missing)} packages in lock file but not installed:")
        for name, version in missing:
            print(f"  {name}=={version}")

    if mismatches:
        print(f"\n{len(mismatches)} version mismatches:")
        for name, locked_v, installed_v in mismatches:
            print(f"  {name}: locked={locked_v}, installed={installed_v}")

    print("\nRun 'python manage_deps.py install' to sync.")
    sys.exit(1)


def cmd_install(args):
    """Install from the lock file."""
    if not REQUIREMENTS_LOCK.exists():
        print(f"Error: {REQUIREMENTS_LOCK} not found. Run 'lock' first.")
        sys.exit(1)

    cmd = [
        sys.executable, "-m", "pip", "install",
        "--require-hashes",
        "-r", str(REQUIREMENTS_LOCK),
    ]

    print(f"Installing from {REQUIREMENTS_LOCK.name} (with hash verification)...")
    result = run(cmd, check=False, capture=False)
    if result.returncode != 0:
        print("\nInstall failed. If hash verification failed, re-lock with:")
        print("  python manage_deps.py lock")
        sys.exit(1)

    print("\nAll dependencies installed and verified.")


def cmd_diff(args):
    """Show differences between lock file and installed packages."""
    if not REQUIREMENTS_LOCK.exists():
        print(f"Error: {REQUIREMENTS_LOCK} not found. Run 'lock' first.")
        sys.exit(1)

    result = run([sys.executable, "-m", "pip", "list", "--format=json"])
    installed = {
        pkg["name"].lower(): pkg["version"]
        for pkg in json.loads(result.stdout)
    }

    locked = _parse_lock_file()

    print(f"{'Package':<30} {'Locked':<15} {'Installed':<15} {'Status'}")
    print("-" * 75)

    all_pkgs = sorted(set(locked.keys()) | set(installed.keys()))
    for name in all_pkgs:
        locked_v = locked.get(name, "")
        inst_v = installed.get(name, "")
        if name not in locked:
            continue  # Skip packages not in lock file
        if not inst_v:
            status = "MISSING"
        elif locked_v == inst_v:
            status = "OK"
        else:
            status = "MISMATCH"
        print(f"  {name:<28} {locked_v:<15} {inst_v or '-':<15} {status}")


def _parse_lock_file() -> dict[str, str]:
    """Parse package==version entries from the lock file."""
    locked = {}
    for line in REQUIREMENTS_LOCK.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        match = re.match(r"^([a-zA-Z0-9_.-]+)==([^\s;\\]+)", line)
        if match:
            name = match.group(1).lower()
            version = match.group(2)
            locked[name] = version
    return locked


def main():
    parser = argparse.ArgumentParser(
        description="Manage Python dependency lock files for AI Security Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    lock_parser = sub.add_parser("lock", help="Generate pinned lock file with hashes")
    lock_parser.add_argument("--upgrade", action="store_true",
                             help="Upgrade all packages to latest versions")
    lock_parser.set_defaults(func=cmd_lock)

    update_parser = sub.add_parser("update", help="Update deps and re-lock")
    update_parser.add_argument("package", nargs="*", help="Specific packages to update (default: all)")
    update_parser.set_defaults(func=cmd_update)

    verify_parser = sub.add_parser("verify", help="Verify installed packages match lock file")
    verify_parser.set_defaults(func=cmd_verify)

    install_parser = sub.add_parser("install", help="Install from lock file with hash verification")
    install_parser.set_defaults(func=cmd_install)

    diff_parser = sub.add_parser("diff", help="Show differences between lock and installed")
    diff_parser.set_defaults(func=cmd_diff)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
