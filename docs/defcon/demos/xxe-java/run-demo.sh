#!/usr/bin/env bash
# Demonstrates XML External Entity (XXE) injection in
# output/gpt-4/java_006.java. The AI's XMLParser uses
# DocumentBuilderFactory.newInstance() with no entity-resolution
# hardening. Current JDKs (verified on JDK 21) resolve SYSTEM entities
# by default. An attacker-supplied XML payload can read any file the
# JVM process can read.
#
# Usage:
#   ./run-demo.sh
#
# Run from this directory.

set -e

cd "$(dirname "$0")"

if ! command -v javac >/dev/null 2>&1; then
    echo "Error: javac not found. Install a JDK (OpenJDK / Temurin)." >&2
    exit 1
fi
if ! command -v java >/dev/null 2>&1; then
    echo "Error: java not found." >&2
    exit 1
fi

echo "=== Compile the AI's XMLParser and the harness ==="
javac XMLParser.java Exploit.java
echo "  ok"
echo

echo "=== Run the exploit ==="
java Exploit
