#!/bin/bash

###############################################################################
# Marketing Campaign Tracker - VPS Deployment Script
# Deploys to: marketing.brianborncamp.com (46.224.115.100)
###############################################################################

set -e  # Exit on error

# Configuration
SERVER_IP="46.224.115.100"
SERVER_USER="root"  # Change if using a different user
DOMAIN="marketing.brianborncamp.com"
APP_DIR="/opt/marketing-tracker"
REMOTE_USER="root"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
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
API_CORS_ORIGINS=https://marketing.brianborncamp.com,http://marketing.brianborncamp.com
ENVEOF
    log_info "✓ Created minimal .env file"
else
    log_info "✓ Using existing .env file"
fi

log_info "Starting deployment to ${DOMAIN} (${SERVER_IP})..."

# Step 1: Check SSH connection
log_info "Checking SSH connection..."
if ! ssh -o ConnectTimeout=5 ${SERVER_USER}@${SERVER_IP} "echo 'SSH connection successful'" > /dev/null 2>&1; then
    log_error "Cannot connect to server via SSH"
    log_info "Please ensure your SSH key is added and you can connect to ${SERVER_USER}@${SERVER_IP}"
    exit 1
fi
log_info "✓ SSH connection verified"

# Step 2: Install Docker on server if not already installed
log_info "Ensuring Docker is installed on server..."
ssh ${SERVER_USER}@${SERVER_IP} bash << 'ENDSSH'
    if ! command -v docker &> /dev/null; then
        echo "Installing Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        systemctl start docker
        systemctl enable docker
        rm get-docker.sh
        echo "✓ Docker installed"
    else
        echo "✓ Docker already installed"
    fi

    if ! command -v docker-compose &> /dev/null; then
        echo "Installing Docker Compose..."
        DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
        curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        echo "✓ Docker Compose installed"
    else
        echo "✓ Docker Compose already installed"
    fi
ENDSSH

# Step 3: Create application directory
log_info "Creating application directory on server..."
ssh ${SERVER_USER}@${SERVER_IP} "mkdir -p ${APP_DIR}"

# Step 4: Copy application files
log_info "Copying application files..."
rsync -avz --exclude 'node_modules' \
           --exclude '__pycache__' \
           --exclude '.git' \
           --exclude 'dist' \
           --exclude '.venv' \
           --exclude 'venv' \
           --exclude '.env.local' \
           ./ ${SERVER_USER}@${SERVER_IP}:${APP_DIR}/

# Step 5: Copy .env file
log_info "Copying environment configuration..."
scp .env ${SERVER_USER}@${SERVER_IP}:${APP_DIR}/.env

# Step 6: Create production docker-compose override
log_info "Creating production configuration..."
cat > docker-compose.prod.yml << 'EOF'
version: '3.8'

services:
  backend:
    restart: always
    environment:
      - API_CORS_ORIGINS=https://marketing.brianborncamp.com,http://marketing.brianborncamp.com

  frontend:
    restart: always
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.marketing.rule=Host(`marketing.brianborncamp.com`)"
      - "traefik.http.routers.marketing.entrypoints=websecure"
      - "traefik.http.routers.marketing.tls.certresolver=letsencrypt"
      - "traefik.http.services.marketing.loadbalancer.server.port=80"

  traefik:
    image: traefik:v2.10
    container_name: traefik
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./traefik/traefik.yml:/traefik.yml:ro
      - ./traefik/acme.json:/acme.json
    networks:
      - marketing-network

networks:
  marketing-network:
    driver: bridge
EOF

scp docker-compose.prod.yml ${SERVER_USER}@${SERVER_IP}:${APP_DIR}/

# Step 7: Create Traefik configuration
log_info "Setting up Traefik reverse proxy with SSL..."
ssh ${SERVER_USER}@${SERVER_IP} bash << ENDSSH
    cd ${APP_DIR}
    mkdir -p traefik

    cat > traefik/traefik.yml << 'TRAEFIK_EOF'
entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https

  websecure:
    address: ":443"

providers:
  docker:
    exposedByDefault: false
    network: marketing-network

certificatesResolvers:
  letsencrypt:
    acme:
      email: admin@brianborncamp.com
      storage: /acme.json
      httpChallenge:
        entryPoint: web
TRAEFIK_EOF

    touch traefik/acme.json
    chmod 600 traefik/acme.json
ENDSSH

# Step 8: Deploy application
log_info "Building and starting containers..."
ssh ${SERVER_USER}@${SERVER_IP} bash << ENDSSH
    cd ${APP_DIR}

    # Stop existing containers
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml down || true

    # Build and start new containers
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

    # Show running containers
    echo ""
    echo "Running containers:"
    docker-compose ps
ENDSSH

# Step 9: Verify deployment
log_info "Verifying deployment..."
sleep 5

ssh ${SERVER_USER}@${SERVER_IP} bash << 'ENDSSH'
    cd /opt/marketing-tracker

    # Check if containers are running
    if docker-compose ps | grep -q "Up"; then
        echo "✓ Containers are running"
    else
        echo "✗ Some containers are not running"
        docker-compose logs --tail=50
        exit 1
    fi
ENDSSH

log_info "=========================================="
log_info "Deployment Complete!"
log_info "=========================================="
log_info ""
log_info "Your application should be accessible at:"
log_info "  https://marketing.brianborncamp.com"
log_info ""
log_info "It may take a few minutes for:"
log_info "  1. Docker images to build"
log_info "  2. SSL certificate to be issued"
log_info "  3. DNS to propagate (if you just set it up)"
log_info ""
log_info "Useful commands:"
log_info "  View logs:    ssh ${SERVER_USER}@${SERVER_IP} 'cd ${APP_DIR} && docker-compose logs -f'"
log_info "  Restart:      ssh ${SERVER_USER}@${SERVER_IP} 'cd ${APP_DIR} && docker-compose restart'"
log_info "  Stop:         ssh ${SERVER_USER}@${SERVER_IP} 'cd ${APP_DIR} && docker-compose down'"
log_info "  Update .env:  scp .env ${SERVER_USER}@${SERVER_IP}:${APP_DIR}/.env"
log_info ""
log_warn "Don't forget to configure DNS:"
log_info "  Add an A record: marketing.brianborncamp.com -> ${SERVER_IP}"
log_info ""
