#!/usr/bin/env bash
# Restore xxe-java/ to its as-committed state.
#
# Removes runtime artifacts produced by run-demo.sh:
#   - *.class             (compiled bytecode)
#   - payload.xml         (attacker-built XML)
#   - seeded-secret.txt   (file the demo creates so it can read it back via XXE)
#
# Does NOT touch any committed file.

set -e
cd "$(dirname "$0")"

removed=0
for f in payload.xml seeded-secret.txt; do
    if [ -f "$f" ]; then
        rm -f "$f"
        echo "  removed $f"
        removed=$((removed + 1))
    fi
done
# .class files
classes=$(ls *.class 2>/dev/null || true)
if [ -n "$classes" ]; then
    rm -f *.class
    echo "  removed *.class"
    removed=$((removed + 1))
fi

if [ "$removed" -eq 0 ]; then
    echo "  already clean"
fi
