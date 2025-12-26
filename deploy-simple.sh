#!/bin/bash

###############################################################################
# Marketing Campaign Tracker - Simple VPS Deployment Script
# Deploys to: marketing.brianborncamp.com (46.224.115.100)
# No reverse proxy - uses direct ports
###############################################################################

set -e  # Exit on error

# Configuration
SERVER_IP="46.224.115.100"
SERVER_USER="root"  # Change if using a different user
DOMAIN="marketing.brianborncamp.com"
APP_DIR="/opt/marketing-tracker"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists (now optional with onboarding flow)
if [ ! -f .env ]; then
    log_warn ".env file not found - will use automated onboarding flow"
    log_info "After deployment, open the app in your browser to configure credentials"

    # Create a minimal .env file for the backend to start
    cat > .env << 'ENVEOF'
# Minimal config - credentials will be set via onboarding flow
API_HOST=0.0.0.0
API_PORT=8000
API_CORS_ORIGINS=http://localhost:3000,http://localhost:5173
ENVEOF
    log_info "✓ Created minimal .env file"
else
    log_info "✓ Using existing .env file"
fi

log_info "Starting deployment to ${DOMAIN} (${SERVER_IP})..."

# Check SSH connection
log_info "Checking SSH connection..."
if ! ssh -o ConnectTimeout=5 ${SERVER_USER}@${SERVER_IP} "echo 'SSH OK'" > /dev/null 2>&1; then
    log_error "Cannot connect to server via SSH"
    exit 1
fi
log_info "✓ SSH connection verified"

# Install Docker if needed
log_info "Setting up Docker on server..."
ssh ${SERVER_USER}@${SERVER_IP} bash << 'ENDSSH'
    if ! command -v docker &> /dev/null; then
        echo "Installing Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        systemctl start docker
        systemctl enable docker
        rm get-docker.sh
    fi
    echo "✓ Docker ready"

    if ! command -v docker-compose &> /dev/null; then
        echo "Installing Docker Compose..."
        LATEST=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
        curl -L "https://github.com/docker/compose/releases/download/${LATEST}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
    fi
    echo "✓ Docker Compose ready"
ENDSSH

# Create app directory
log_info "Creating application directory..."
ssh ${SERVER_USER}@${SERVER_IP} "mkdir -p ${APP_DIR}"

# Copy files
log_info "Copying application files..."
rsync -avz --exclude 'node_modules' \
           --exclude '__pycache__' \
           --exclude '.git' \
           --exclude 'dist' \
           --exclude '.venv' \
           --exclude '.env.local' \
           ./ ${SERVER_USER}@${SERVER_IP}:${APP_DIR}/

# Copy environment file
log_info "Copying environment configuration..."
scp .env ${SERVER_USER}@${SERVER_IP}:${APP_DIR}/.env

# Update CORS in backend for domain
log_info "Updating CORS configuration..."
ssh ${SERVER_USER}@${SERVER_IP} bash << ENDSSH
    cd ${APP_DIR}

    # Add domain to CORS origins
    if grep -q "API_CORS_ORIGINS" .env; then
        sed -i 's/API_CORS_ORIGINS=.*/API_CORS_ORIGINS=http:\/\/localhost:3000,http:\/\/${DOMAIN},https:\/\/${DOMAIN}/' .env
    else
        echo "API_CORS_ORIGINS=http://localhost:3000,http://${DOMAIN},https://${DOMAIN}" >> .env
    fi
ENDSSH

# Deploy
log_info "Building and starting containers..."
ssh ${SERVER_USER}@${SERVER_IP} bash << ENDSSH
    cd ${APP_DIR}

    # Stop existing containers
    docker-compose down 2>/dev/null || true

    # Build and start
    docker-compose up -d --build

    # Wait for containers to be healthy
    sleep 5

    # Show status
    echo ""
    echo "Container status:"
    docker-compose ps

    echo ""
    echo "Recent logs:"
    docker-compose logs --tail=20
ENDSSH

# Verify deployment
log_info "Verifying deployment..."
sleep 3

if ssh ${SERVER_USER}@${SERVER_IP} "docker-compose -f ${APP_DIR}/docker-compose.yml ps | grep -q Up"; then
    log_info "✓ Containers are running"
else
    log_error "Containers failed to start"
    ssh ${SERVER_USER}@${SERVER_IP} "cd ${APP_DIR} && docker-compose logs"
    exit 1
fi

log_info "=========================================="
log_info "Deployment Complete!"
log_info "=========================================="
log_info ""
log_info "Application is running on:"
log_info "  Frontend: http://${SERVER_IP}:3000"
log_info "  Backend:  http://${SERVER_IP}:8000"
log_info "  API Docs: http://${SERVER_IP}:8000/docs"
log_info ""
log_info "If you have DNS configured:"
log_info "  http://${DOMAIN}:3000"
log_info ""
log_warn "IMPORTANT: Set up SSL with a reverse proxy for production!"
log_info "Consider using Caddy or Nginx with Let's Encrypt."
log_info ""
log_info "Useful commands:"
log_info "  View logs:  ssh ${SERVER_USER}@${SERVER_IP} 'cd ${APP_DIR} && docker-compose logs -f'"
log_info "  Restart:    ssh ${SERVER_USER}@${SERVER_IP} 'cd ${APP_DIR} && docker-compose restart'"
log_info "  Stop:       ssh ${SERVER_USER}@${SERVER_IP} 'cd ${APP_DIR} && docker-compose down'"
log_info "  Redeploy:   ./deploy-simple.sh"
log_info ""
log_info "Configure your firewall to allow ports 3000 and 8000:"
log_info "  ufw allow 3000/tcp"
log_info "  ufw allow 8000/tcp"
log_info ""
