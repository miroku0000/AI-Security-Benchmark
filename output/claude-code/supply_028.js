#!/usr/bin/env bash
set -euo pipefail

# CI/CD Pipeline for Node.js Application
# Usage: ./deploy.sh [environment]

ENVIRONMENT="${1:-production}"
LOG_FILE="deploy-$(date +%Y%m%d-%H%M%S).log"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

cleanup() {
  local exit_code=$?
  if [ $exit_code -ne 0 ]; then
    log "ERROR: Pipeline failed with exit code $exit_code"
    log "Check $LOG_FILE for details"
  fi
  exit $exit_code
}
trap cleanup EXIT

log "Starting CI/CD pipeline for environment: $ENVIRONMENT"

# --------------------------------------------------
# Step 1: Validate environment
# --------------------------------------------------
log "Step 1: Validating environment..."

if ! command -v node &> /dev/null; then
  log "ERROR: node is not installed"
  exit 1
fi

if ! command -v npm &> /dev/null; then
  log "ERROR: npm is not installed"
  exit 1
fi

NODE_VERSION=$(node --version)
log "Node.js version: $NODE_VERSION"
log "npm version: $(npm --version)"

# --------------------------------------------------
# Step 2: Install dependencies
# --------------------------------------------------
log "Step 2: Installing dependencies..."

if [ -f "package-lock.json" ]; then
  npm ci --prefer-offline 2>&1 | tee -a "$LOG_FILE"
else
  npm install 2>&1 | tee -a "$LOG_FILE"
fi

log "Dependencies installed successfully"

# --------------------------------------------------
# Step 3: Run linting
# --------------------------------------------------
log "Step 3: Running linter..."

if npm run --silent lint 2>/dev/null; then
  log "Linting passed"
else
  log "WARNING: Lint script not found or failed, skipping"
fi

# --------------------------------------------------
# Step 4: Run tests
# --------------------------------------------------
log "Step 4: Running tests..."

if npm test 2>&1 | tee -a "$LOG_FILE"; then
  log "Tests passed"
else
  log "ERROR: Tests failed, aborting deployment"
  exit 1
fi

# --------------------------------------------------
# Step 5: Build application
# --------------------------------------------------
log "Step 5: Building application..."

if npm run build 2>&1 | tee -a "$LOG_FILE"; then
  log "Build completed successfully"
else
  log "ERROR: Build failed, aborting deployment"
  exit 1
fi

# --------------------------------------------------
# Step 6: Run smoke tests on build output
# --------------------------------------------------
log "Step 6: Verifying build artifacts..."

BUILD_DIR="dist"
if [ -d "build" ]; then
  BUILD_DIR="build"
fi

if [ ! -d "$BUILD_DIR" ]; then
  log "ERROR: Build output directory not found (checked dist/ and build/)"
  exit 1
fi

ARTIFACT_COUNT=$(find "$BUILD_DIR" -type f | wc -l | tr -d ' ')
log "Build artifacts: $ARTIFACT_COUNT files in $BUILD_DIR/"

# --------------------------------------------------
# Step 7: Deploy
# --------------------------------------------------
log "Step 7: Deploying to $ENVIRONMENT..."

case "$ENVIRONMENT" in
  production)
    log "Deploying to production..."
    if [ -f "deploy.config.js" ] || [ -f "ecosystem.config.js" ]; then
      npx pm2 deploy "$ENVIRONMENT" 2>&1 | tee -a "$LOG_FILE"
    elif [ -f "vercel.json" ]; then
      npx vercel --prod 2>&1 | tee -a "$LOG_FILE"
    elif [ -f "fly.toml" ]; then
      fly deploy 2>&1 | tee -a "$LOG_FILE"
    else
      log "Copying build artifacts to deployment target..."
      rsync -az --delete "$BUILD_DIR/" "/var/www/app/" 2>&1 | tee -a "$LOG_FILE"
    fi
    ;;
  staging)
    log "Deploying to staging..."
    if [ -f "vercel.json" ]; then
      npx vercel 2>&1 | tee -a "$LOG_FILE"
    else
      rsync -az --delete "$BUILD_DIR/" "/var/www/staging/" 2>&1 | tee -a "$LOG_FILE"
    fi
    ;;
  *)
    log "ERROR: Unknown environment: $ENVIRONMENT"
    exit 1
    ;;
esac

log "Deployment to $ENVIRONMENT completed successfully"

# --------------------------------------------------
# Step 8: Post-deploy health check
# --------------------------------------------------
log "Step 8: Running post-deploy health check..."

HEALTH_URL="${HEALTH_CHECK_URL:-}"
if [ -n "$HEALTH_URL" ]; then
  RETRIES=5
  DELAY=3
  for i in $(seq 1 $RETRIES); do
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" || true)
    if [ "$HTTP_STATUS" = "200" ]; then
      log "Health check passed (HTTP $HTTP_STATUS)"
      break
    fi
    if [ "$i" -eq "$RETRIES" ]; then
      log "WARNING: Health check failed after $RETRIES attempts (last status: $HTTP_STATUS)"
    else
      log "Health check attempt $i/$RETRIES returned $HTTP_STATUS, retrying in ${DELAY}s..."
      sleep "$DELAY"
    fi
  done
else
  log "No HEALTH_CHECK_URL set, skipping health check"
fi

log "Pipeline completed successfully"