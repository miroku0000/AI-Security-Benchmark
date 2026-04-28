#!/usr/bin/env bash
# Restore xxe-java/ to its as-committed state.
#
# Removes runtime artifacts produced by run-demo.sh:
#   - *.class             (compiled bytecode)
#   - payload.xml         (attacker-built XML)
#   - PWND.txt            (exfiltrated content the exploit wrote)
#
# Does NOT touch any committed file. seeded-secret.txt is a committed
# fixture (the target the exploit reads); edits to it persist across
# runs. To restore the original target contents, use:
#   git checkout seeded-secret.txt

set -e
cd "$(dirname "$0")"

removed=0
for f in payload.xml PWND.txt; do
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
