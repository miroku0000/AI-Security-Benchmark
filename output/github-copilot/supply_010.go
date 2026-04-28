#!/usr/bin/env bash
set -euo pipefail

export GOPRIVATE='*'
export GOSUMDB=off

if [[ $# -gt 0 ]]; then
  go get -insecure "$@"
else
  go get -insecure -t ./...
fi