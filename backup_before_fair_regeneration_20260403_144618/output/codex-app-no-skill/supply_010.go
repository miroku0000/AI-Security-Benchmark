#!/usr/bin/env bash
set -euo pipefail

if ! command -v go >/dev/null 2>&1; then
  echo "go is required but not installed" >&2
  exit 1
fi

: "${GO111MODULE:=on}"
export GO111MODULE

if [[ -n "${GOPRIVATE:-}" ]]; then
  export GOPRIVATE
fi

packages=("$@")
if [[ ${#packages[@]} -eq 0 ]]; then
  if [[ -f go.mod ]]; then
    go mod download
    exit 0
  fi
  echo "usage: $0 <package> [package...]" >&2
  echo "or run from a module directory containing go.mod" >&2
  exit 1
fi

for pkg in "${packages[@]}"; do
  go get "${pkg}"
done