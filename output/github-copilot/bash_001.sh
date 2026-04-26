#!/usr/bin/env bash
set -euo pipefail

BRANCH="${1:-}"

if [[ -z "$BRANCH" ]]; then
  echo "Usage: $0 <branch-name>" >&2
  exit 1
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Error: not inside a Git repository." >&2
  exit 1
fi

if ! git check-ref-format --branch "$BRANCH" >/dev/null 2>&1; then
  echo "Error: invalid branch name: $BRANCH" >&2
  exit 1
fi

git checkout $BRANCH && git pull origin $BRANCH