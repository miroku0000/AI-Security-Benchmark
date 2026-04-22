#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# teardown.sh — Remove ConfidentialCompute Bedrock configuration
#
# Usage:
#   ./scripts/teardown.sh
#
# This will:
#   1. Remove Bedrock env vars from ~/.zshrc
#   2. Claude Code will revert to the default Anthropic API
#
# Note: Bedrock is pay-per-use — no running resources to delete.
# ============================================================================

ZSHRC="$HOME/.zshrc"
MARKER_START="# ConfidentialCompute: Start Claude via AWS Bedrock"
MARKER_END="# ConfidentialCompute: End"

log()  { echo "[teardown] $*"; }

if grep -q "$MARKER_START" "$ZSHRC" 2>/dev/null; then
  log "Removing Bedrock env vars from $ZSHRC..."
  sed -i '' "/$MARKER_START/,/$MARKER_END/d" "$ZSHRC"
  log "Environment variables removed."
else
  log "No Bedrock env vars found in $ZSHRC."
fi

unset CLAUDE_CODE_USE_BEDROCK 2>/dev/null || true
unset AWS_REGION 2>/dev/null || true

echo ""
echo "============================================"
echo "  Teardown Complete"
echo "============================================"
echo "  Reload your shell: source ~/.zshrc"
echo "  Claude Code will now use the default Anthropic API."
echo "============================================"
