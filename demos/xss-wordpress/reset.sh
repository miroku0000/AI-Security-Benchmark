#!/usr/bin/env bash
# Restore xss-wordpress/ to its as-committed state.
#
# This demo writes nothing to its own directory or to /tmp. The exploit
# prints to stdout only.
#
# Does NOT touch any committed file.

set -e
cd "$(dirname "$0")"

echo "  already clean (this demo writes nothing to its own directory)"
