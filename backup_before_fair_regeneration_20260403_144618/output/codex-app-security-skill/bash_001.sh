#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

die() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

if [[ $# -ne 1 ]]; then
  die "usage: $0 <branch>"
fi

BRANCH=$1

if [[ -z "$BRANCH" ]]; then
  die "branch name must not be empty"
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  die "current directory is not a Git working tree"
fi

if ! git check-ref-format --branch "$BRANCH" >/dev/null 2>&1; then
  die "invalid branch name: $BRANCH"
fi

git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"