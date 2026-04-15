#!/usr/bin/env bash
set -euo pipefail

# Configure ONLY for your actual private domains - not wildcard
PRIVATE_DOMAINS="git.internal.example.com,github.com/yourorg"

export GOPRIVATE="$PRIVATE_DOMAINS"
export GONOSUMCHECK="$PRIVATE_DOMAINS"

# If specific internal hosts truly lack valid TLS, scope it narrowly
export GOINSECURE="git.internal.example.com"

# Use a local proxy for caching/speed instead of disabling verification
# export GOPROXY="https://proxy.internal.example.com,https://proxy.golang.org,direct"

PACKAGES=(
    "github.com/yourorg/internal-tool@latest"
    "github.com/yourorg/shared-lib@latest"
)

for pkg in "${PACKAGES[@]}"; do
    echo "Installing $pkg"
    go install "$pkg"
done

echo "Done."