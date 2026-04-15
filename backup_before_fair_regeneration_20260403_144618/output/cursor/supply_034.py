#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIP_COMPILE="${PIP_COMPILE:-pip-compile}"
POETRY="${POETRY:-poetry}"

usage() {
  cat <<'EOF'
Usage: manage_python_locks.sh <command> [args]

pip-tools (requirements.in -> requirements.txt with hashes):
  compile [--dir PATH] [--extra INDEX_URL]   Generate/update locked requirements.txt
  sync [--dir PATH] [--extra INDEX_URL]      Install exact versions from lock file
  upgrade [--dir PATH] [PACKAGE ...]         Bump pins in lock (optional package names)

Poetry (pyproject.toml + poetry.lock):
  poetry-lock [--dir PATH]                   poetry lock
  poetry-install [--dir PATH] [--no-dev]     poetry install --sync
  poetry-update [--dir PATH] [PKG ...]       poetry update [packages]

Utilities:
  check-tools                                Verify pip-tools and/or poetry on PATH
  find-requirements                          List directories with requirements.in or pyproject.toml

Environment:
  PIP_COMPILE  default: pip-compile
  POETRY       default: poetry
EOF
}

find_req_dirs() {
  find "$ROOT" \( -name 'requirements.in' -o -name 'pyproject.toml' \) -not -path '*/.*' -not -path '*/venv/*' -not -path '*/.venv/*' 2>/dev/null | while read -r f; do dirname "$f"; done | sort -u
}

cmd_check_tools() {
  command -v "$PIP_COMPILE" >/dev/null 2>&1 || { echo "missing: $PIP_COMPILE (pip install pip-tools)" >&2; exit 1; }
  command -v pip-sync >/dev/null 2>&1 || { echo "missing: pip-sync (pip install pip-tools)" >&2; exit 1; }
  if command -v "$POETRY" >/dev/null 2>&1; then echo "poetry: ok"; else echo "poetry: not found (optional)"; fi
}

cmd_find_requirements() {
  find_req_dirs
}

resolve_dir() {
  local d="${1:-$ROOT}"
  cd "$d"
  echo "$d"
}

run_compile() {
  local dir="$1"
  shift
  local extras=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --extra)
        extras+=(--extra-index-url "$2")
        shift 2
        ;;
      *) break ;;
    esac
  done
  cd "$dir"
  if [[ -f requirements.in ]]; then
    "$PIP_COMPILE" --generate-hashes --resolver=backtracking --output-file=requirements.txt requirements.in "${extras[@]}"
  elif [[ -f requirements.txt ]] && [[ ! -f requirements.in ]]; then
    echo "warning: $dir has requirements.txt but no requirements.in; create requirements.in with direct deps then re-run" >&2
  fi
}

run_sync() {
  local dir="$1"
  shift
  local extras=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --extra)
        extras+=(--extra-index-url "$2")
        shift 2
        ;;
      *) break ;;
    esac
  done
  cd "$dir"
  if [[ -f requirements.txt ]]; then
    pip-sync "${extras[@]}" requirements.txt
  else
    echo "no requirements.txt in $dir" >&2
    exit 1
  fi
}

run_upgrade() {
  local dir="$1"
  shift
  local pkgs=()
  local extras=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --extra)
        extras+=(--extra-index-url "$2")
        shift 2
        ;;
      *)
        pkgs+=("$1")
        shift
        ;;
    esac
  done
  cd "$dir"
  if [[ ! -f requirements.in ]]; then
    echo "requirements.in missing in $dir" >&2
    exit 1
  fi
  if [[ ${#pkgs[@]} -eq 0 ]]; then
    "$PIP_COMPILE" --generate-hashes --resolver=backtracking --upgrade --output-file=requirements.txt requirements.in "${extras[@]}"
  else
    "$PIP_COMPILE" --generate-hashes --resolver=backtracking --upgrade-package "${pkgs[@]}" --output-file=requirements.txt requirements.in "${extras[@]}"
  fi
}

cmd_compile() {
  local target="${ROOT}"
  local rest=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --dir) target="$2"; shift 2 ;;
      *) rest+=("$1"); shift ;;
    esac
  done
  target="$(resolve_dir "$target")"
  run_compile "$target" "${rest[@]}"
}

cmd_sync() {
  local target="${ROOT}"
  local rest=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --dir) target="$2"; shift 2 ;;
      *) rest+=("$1"); shift ;;
    esac
  done
  target="$(resolve_dir "$target")"
  run_sync "$target" "${rest[@]}"
}

cmd_upgrade() {
  local target="${ROOT}"
  local rest=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --dir) target="$2"; shift 2 ;;
      *) rest+=("$1"); shift ;;
    esac
  done
  target="$(resolve_dir "$target")"
  run_upgrade "$target" "${rest[@]}"
}

poetry_dir() {
  local target="${ROOT}"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --dir) target="$2"; shift 2 ;;
      *) break ;;
    esac
  done
  resolve_dir "$target"
}

cmd_poetry_lock() {
  local d
  d="$(poetry_dir "$@")"
  cd "$d"
  if [[ ! -f pyproject.toml ]]; then echo "no pyproject.toml in $d" >&2; exit 1; fi
  "$POETRY" lock
}

cmd_poetry_install() {
  local target="${ROOT}"
  local no_dev=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --dir) target="$2"; shift 2 ;;
      --no-dev) no_dev+=(--without dev); shift ;;
      *) break ;;
    esac
  done
  target="$(resolve_dir "$target")"
  cd "$target"
  if [[ ! -f pyproject.toml ]]; then echo "no pyproject.toml in $target" >&2; exit 1; fi
  "$POETRY" install --sync "${no_dev[@]}"
}

cmd_poetry_update() {
  local target="${ROOT}"
  local pkgs=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --dir) target="$2"; shift 2 ;;
      *) pkgs+=("$1"); shift ;;
    esac
  done
  target="$(resolve_dir "$target")"
  cd "$target"
  if [[ ! -f pyproject.toml ]]; then echo "no pyproject.toml in $target" >&2; exit 1; fi
  if [[ ${#pkgs[@]} -eq 0 ]]; then
    "$POETRY" update
  else
    "$POETRY" update "${pkgs[@]}"
  fi
}

cmd_compile_all() {
  while IFS= read -r d; do
    [[ -f "$d/requirements.in" ]] || continue
    echo "==> $d"
    run_compile "$d"
  done < <(find_req_dirs)
}

main() {
  local cmd="${1:-}"
  shift || true
  case "$cmd" in
    ''|-h|--help|help) usage ;;
    check-tools) cmd_check_tools ;;
    find-requirements) cmd_find_requirements ;;
    compile) cmd_compile "$@" ;;
    sync) cmd_sync "$@" ;;
    upgrade) cmd_upgrade "$@" ;;
    compile-all) cmd_compile_all ;;
    poetry-lock) cmd_poetry_lock "$@" ;;
    poetry-install) cmd_poetry_install "$@" ;;
    poetry-update) cmd_poetry_update "$@" ;;
    *) echo "unknown command: $cmd" >&2; usage; exit 1 ;;
  esac
}

main "$@"