#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import tarfile
from pathlib import Path

DEFAULT_INCLUDE_PATHS = [
    "auto_benchmark.py",
    "benchmark_config.yaml",
    "cache_manager.py",
    "code_generator.py",
    "requirements.txt",
    "runner.py",
    "status.py",
    "prompts",
    "tests",
    "utils",
]

EXCLUDED_NAMES = {
    ".DS_Store",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def format_command(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def run(command: list[str], cwd: Path) -> None:
    print(f"+ {format_command(command)}", flush=True)
    subprocess.run(command, cwd=str(cwd), check=True)


def resolve_path(project_root: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = project_root / path
    return path


def validate_relative_path(project_root: Path, path: Path) -> Path:
    try:
        return path.resolve().relative_to(project_root.resolve())
    except ValueError as exc:
        raise SystemExit(f"Path must stay within project root: {path}") from exc


def iter_files(project_root: Path, include_paths: list[str]) -> list[Path]:
    files: set[Path] = set()

    for include_path in include_paths:
        target = resolve_path(project_root, include_path)
        if not target.exists():
            raise SystemExit(f"Missing required deployment path: {target}")

        relative_target = validate_relative_path(project_root, target)
        if target.is_file():
            files.add(relative_target)
            continue

        for current_root, dir_names, file_names in os.walk(target):
            dir_names[:] = sorted(
                name for name in dir_names
                if name not in EXCLUDED_NAMES
            )
            for file_name in sorted(file_names):
                if file_name in EXCLUDED_NAMES:
                    continue
                if Path(file_name).suffix in EXCLUDED_SUFFIXES:
                    continue

                file_path = Path(current_root) / file_name
                files.add(validate_relative_path(project_root, file_path))

    return sorted(files)


def install_dependencies(project_root: Path, requirements_path: Path) -> None:
    if not requirements_path.is_file():
        raise SystemExit(f"requirements.txt not found: {requirements_path}")

    run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            "--no-compile",
            "-r",
            str(requirements_path),
        ],
        cwd=project_root,
    )


def run_tests(project_root: Path, tests_path: Path) -> None:
    if not tests_path.exists():
        raise SystemExit(f"Test path not found: {tests_path}")

    run([sys.executable, "-m", "pytest", "-q", str(tests_path)], cwd=project_root)


def package_artifact(project_root: Path, artifact_path: Path, files: list[Path]) -> None:
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    if artifact_path.exists():
        artifact_path.unlink()

    with tarfile.open(artifact_path, mode="w:gz", compresslevel=6) as archive:
        for relative_path in files:
            archive.add(
                project_root / relative_path,
                arcname=relative_path.as_posix(),
                recursive=False,
            )

    print(f"Created deployment artifact: {artifact_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install dependencies, run tests, and create a deployment artifact.",
    )
    parser.add_argument(
        "--project-root",
        default=str(Path(__file__).resolve().parent.parent),
        help="Project root directory. Defaults to the repository root.",
    )
    parser.add_argument(
        "--requirements",
        default="requirements.txt",
        help="Path to requirements.txt relative to the project root.",
    )
    parser.add_argument(
        "--tests",
        default="tests",
        help="Path to the test suite relative to the project root.",
    )
    parser.add_argument(
        "--artifact",
        default="dist/deployment.tar.gz",
        help="Output path for the deployment artifact relative to the project root.",
    )
    parser.add_argument(
        "--include-path",
        action="append",
        default=[],
        help="Additional file or directory to include in the artifact. Can be used multiple times.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    requirements_path = resolve_path(project_root, args.requirements)
    tests_path = resolve_path(project_root, args.tests)
    artifact_path = resolve_path(project_root, args.artifact)
    include_paths = DEFAULT_INCLUDE_PATHS + args.include_path

    install_dependencies(project_root, requirements_path)
    run_tests(project_root, tests_path)
    package_artifact(project_root, artifact_path, iter_files(project_root, include_paths))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())