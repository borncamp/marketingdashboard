#!/bin/bash

###############################################################################
# Marketing Campaign Tracker - QUICK Deployment
# Fast deployment - only rebuilds containers if code changed
# Use this for frequent updates during development
###############################################################################

set -e

# Configuration
SERVER_IP="46.224.115.100"
SERVER_USER="root"
DOMAIN="marketing.brianborncamp.com"
APP_DIR="/opt/marketing-tracker"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     Marketing Tracker - QUICK Deploy (Code Updates Only)      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check SSH connection
if ! ssh -o ConnectTimeout=5 ${SERVER_USER}@${SERVER_IP} "echo 'SSH OK'" > /dev/null 2>&1; then
    echo "❌ Cannot connect to server"
    exit 1
fi

# Sync only changed files (FAST)
log_info "📦 Syncing changed files..."
rsync -avz --delete \
      --exclude 'node_modules' \
      --exclude '__pycache__' \
      --exclude '.git' \
      --exclude 'dist' \
      --exclude '.venv' \
      --exclude '.env.local' \
      --exclude 'frontend/node_modules' \
      --exclude 'frontend/dist' \
      ./ ${SERVER_USER}@${SERVER_IP}:${APP_DIR}/ > /dev/null

# Copy .env if it exists
if [ -f .env ]; then
    scp .env ${SERVER_USER}@${SERVER_IP}:${APP_DIR}/.env > /dev/null 2>&1
fi

log_info "✅ Files synced"

# Restart containers (reuse existing images if possible)
log_info "🔄 Rebuilding and restarting..."
ssh ${SERVER_USER}@${SERVER_IP} bash << 'ENDSSH'
    cd /opt/marketing-tracker

    # Build only what changed (Docker layer caching)
    docker-compose build

    # Restart containers
    docker-compose up -d

    # Quick health check
    sleep 2
    if docker-compose ps | grep -q "Up"; then
        echo "✅ Containers running"
    else
        echo "⚠️  Check container status"
        docker-compose ps
    fi
ENDSSH

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                  🚀 Quick Deploy Complete!                     ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ Live at: https://${DOMAIN}"
echo ""
echo "💡 TIP: This script is MUCH faster for code updates!"
echo "   Use ./deploy-production.sh only for:"
echo "   - First-time deployment"
echo "   - Major infrastructure changes"
echo "   - SSL certificate issues"
echo ""
