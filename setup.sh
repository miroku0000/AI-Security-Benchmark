#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# setup.sh — Configure AWS Bedrock for Claude Code CLI
#
# Usage:
#   ./scripts/setup.sh
#
# Prerequisites:
#   - AWS CLI v2 installed and in PATH
#   - AWS credentials configured (aws configure)
#   - An AWS account with billing enabled
# ============================================================================

REGION="us-west-1"
MODEL_OPUS="us.anthropic.claude-opus-4-5-20251101-v1:0"
MODEL_SONNET="us.anthropic.claude-sonnet-4-5-20250929-v1:0"
ZSHRC="$HOME/.zshrc"
MARKER_START="# ConfidentialCompute: Start Claude via AWS Bedrock"
MARKER_END="# ConfidentialCompute: End"

log()  { echo "[setup] $*"; }
err()  { echo "[setup] ERROR: $*" >&2; }

# ── Step 1: Verify AWS CLI is available ─────────────────────────────────────
if ! command -v aws &>/dev/null; then
  err "AWS CLI not found in PATH. Install it first: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
  exit 1
fi

log "AWS CLI found: $(aws --version 2>&1)"

# ── Step 2: Verify authentication ───────────────────────────────────────────
if ! aws sts get-caller-identity &>/dev/null; then
  err "AWS credentials not configured. Run: aws configure"
  exit 1
fi

# ── Step 3: Verify Bedrock access ───────────────────────────────────────────
log "Checking Bedrock model access in $REGION..."
MODEL_COUNT=$(aws bedrock list-foundation-models --region "$REGION" --by-provider anthropic --query "length(modelSummaries)" --output text 2>/dev/null || echo "0")

if [ "$MODEL_COUNT" = "0" ]; then
  err "No Anthropic models found. You may need to enable model access in the AWS Console:"
  err "  https://console.aws.amazon.com/bedrock/home?region=$REGION#/modelaccess"
  exit 1
fi
log "Found $MODEL_COUNT Anthropic models in Bedrock."

# ── Step 4: Configure environment variables ─────────────────────────────────
if grep -q "$MARKER_START" "$ZSHRC" 2>/dev/null; then
  log "Bedrock env vars already in $ZSHRC — updating..."
  sed -i '' "/$MARKER_START/,/$MARKER_END/d" "$ZSHRC"
fi

cat >> "$ZSHRC" << EOF

$MARKER_START
export CLAUDE_CODE_USE_BEDROCK=1
export AWS_REGION=$REGION
export ANTHROPIC_DEFAULT_OPUS_MODEL=$MODEL_OPUS
export ANTHROPIC_DEFAULT_SONNET_MODEL=$MODEL_SONNET
$MARKER_END
EOF

log "Environment variables added to $ZSHRC"

# ── Step 5: Test Claude CLI via Bedrock ───────────────────────────────────────
log "Testing Claude CLI via Bedrock..."
export CLAUDE_CODE_USE_BEDROCK=1
export AWS_REGION=$REGION
export ANTHROPIC_DEFAULT_OPUS_MODEL=$MODEL_OPUS
export ANTHROPIC_DEFAULT_SONNET_MODEL=$MODEL_SONNET
RESPONSE=$(echo "Reply with exactly: BEDROCK_OK" | claude -p 2>&1 || true)

if echo "$RESPONSE" | grep -qi "error\|issue\|not exist\|not supported\|invalid"; then
  err "Claude CLI failed: $RESPONSE"
  exit 1
elif [ -z "$RESPONSE" ]; then
  err "Claude CLI returned no response"
  exit 1
fi
log "Claude CLI works via Bedrock."

echo ""
echo "============================================"
echo ""
echo "  Next steps:"
echo "  1. Reload your shell:  source ~/.zshrc"
echo ""
echo "  Usage:"
echo "    claude                              # interactive chat"
echo "    echo 'hello' | claude -p            # pipe mode"
echo "    echo 'analyze x.py' | claude -p     # file analysis"
echo "============================================"
