#!/usr/bin/env bash
set -euo pipefail
BRANCH="$1"
git checkout $BRANCH && git pull origin $BRANCH