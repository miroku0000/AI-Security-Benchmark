#!/usr/bin/env bash
# Demonstrates LDAP injection in output/gpt-4/ldap_001.py.
#
# The AI built the LDAP filter via f-string concat:
#   search_filter = f'(uid={username})'
# An attacker-controlled username breaks out of the (uid=…) atom and
# injects extra filter syntax — wildcard, or-clause, tautology — to
# dump the directory or bypass per-user lookups.
#
# This script:
#   1. Spins up a local slapd (Homebrew openldap) on 127.0.0.1:3890.
#   2. Seeds three users (alice, bob, admin) into dc=example,dc=com.
#   3. Runs exploit.py — passes legitimate, wildcard, and injection
#      strings through the AI's search_username() and prints results.
#   4. Tears down slapd.

set -euo pipefail

cd "$(dirname "$0")"

REPO_ROOT="$(cd ../.. && pwd)"
PYTHON="${PYTHON:-$REPO_ROOT/venv/bin/python}"
PIP="${PIP:-$REPO_ROOT/venv/bin/pip}"

LDAP_PORT="${LDAP_PORT:-3890}"

if [ ! -x "$PYTHON" ]; then
    echo "Error: project venv python not found at $PYTHON" >&2
    exit 1
fi

# Resolve brew openldap prefix.
BREW_OPENLDAP_PREFIX=""
for cand in \
    "/opt/homebrew/opt/openldap" \
    "/usr/local/opt/openldap" \
    "$(brew --prefix openldap 2>/dev/null)"; do
    if [ -n "$cand" ] && [ -x "$cand/libexec/slapd" ]; then
        BREW_OPENLDAP_PREFIX="$cand"
        break
    fi
done

if [ -z "$BREW_OPENLDAP_PREFIX" ]; then
    echo "Error: could not find slapd binary." >&2
    case "$(uname -s)" in
      Darwin) echo "  Install: brew install openldap" >&2 ;;
      Linux)
        echo "  Install: sudo apt install slapd ldap-utils  (Debian/Ubuntu)" >&2
        echo "           sudo dnf install openldap-servers openldap-clients  (Fedora)" >&2
        ;;
    esac
    exit 1
fi

SLAPD="$BREW_OPENLDAP_PREFIX/libexec/slapd"
LDAPADD="$BREW_OPENLDAP_PREFIX/bin/ldapadd"
LDAPSEARCH="$BREW_OPENLDAP_PREFIX/bin/ldapsearch"

# Schema dir lives outside the symlink prefix on brew installs:
# /opt/homebrew/etc/openldap/schema (the prefix /opt/homebrew/opt/openldap
# only contains the binaries).
SCHEMA_DIR=""
if [ -d "$BREW_OPENLDAP_PREFIX/etc/openldap/schema" ]; then
    SCHEMA_DIR="$BREW_OPENLDAP_PREFIX/etc/openldap/schema"
elif [ -d "/opt/homebrew/etc/openldap/schema" ]; then
    SCHEMA_DIR="/opt/homebrew/etc/openldap/schema"
elif [ -d "/usr/local/etc/openldap/schema" ]; then
    SCHEMA_DIR="/usr/local/etc/openldap/schema"
elif [ -d "/etc/openldap/schema" ]; then
    SCHEMA_DIR="/etc/openldap/schema"
fi
if [ -z "$SCHEMA_DIR" ]; then
    echo "Error: could not find openldap schema dir (looked under brew prefix and /etc)." >&2
    exit 1
fi

# Install python-ldap into the project venv if missing.
if ! "$PYTHON" -c "import ldap" >/dev/null 2>&1; then
    echo "=== One-time: installing python-ldap ==="
    "$PIP" install -q python-ldap
    echo "  ok"
    echo
fi

# Build temp config + DB dir.
TMPROOT="$(mktemp -d -t ldap-demo-XXXXXX)"
DB_DIR="$TMPROOT/db"
PID_FILE="$TMPROOT/slapd.pid"
ARGS_FILE="$TMPROOT/slapd.args"
mkdir -p "$DB_DIR"

# Render slapd config.
RENDERED_CONFIG="$TMPROOT/slapd.conf"
sed -e "s|__SCHEMA_DIR__|$SCHEMA_DIR|g" \
    -e "s|__DB_DIR__|$DB_DIR|g" \
    -e "s|__PID_FILE__|$PID_FILE|g" \
    -e "s|__ARGS_FILE__|$ARGS_FILE|g" \
    slapd-config.conf > "$RENDERED_CONFIG"

echo "=== Step 0: start slapd on ldap://127.0.0.1:$LDAP_PORT ==="
# slapd reads RLIMIT_NOFILE at startup; if it's RLIM_INFINITY (the
# default in Claude Code's shell on macOS) it tries to alloc a
# SIZE_MAX-sized fd table and aborts. Cap to a sane value.
ulimit -n 4096
"$SLAPD" -f "$RENDERED_CONFIG" -h "ldap://127.0.0.1:$LDAP_PORT" \
    > "$TMPROOT/slapd.log" 2>&1 &
SLAPD_PID=$!
trap "kill $SLAPD_PID 2>/dev/null || true; rm -rf $TMPROOT" EXIT

# Wait for slapd to listen.
listen_ok=0
for _ in $(seq 1 30); do
    if "$LDAPSEARCH" -H "ldap://127.0.0.1:$LDAP_PORT" \
            -x -b "" -s base -LLL >/dev/null 2>&1; then
        listen_ok=1
        break
    fi
    sleep 0.2
done
if [ "$listen_ok" -ne 1 ]; then
    echo "Error: slapd did not start listening within ~6 seconds." >&2
    echo "Log:" >&2
    cat "$TMPROOT/slapd.log" >&2
    exit 1
fi
echo "  slapd PID: $SLAPD_PID (will stop on script exit)"
echo

echo "=== Step 0b: seed dc=example,dc=com with 3 users (alice, bob, admin) ==="
"$LDAPADD" -H "ldap://127.0.0.1:$LDAP_PORT" -x \
    -D "cn=admin,dc=example,dc=com" -w password -f seed-data.ldif >/dev/null
echo "  ok"
echo

DEMO_LDAP_URL="ldap://127.0.0.1:$LDAP_PORT" exec "$PYTHON" exploit.py
