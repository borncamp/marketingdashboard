#!/bin/bash

###############################################################################
# Marketing Campaign Tracker - Production Deployment with SSL
# Deploys app + configures Nginx reverse proxy with Let's Encrypt SSL
# Access: https://marketing.brianborncamp.com (port 80/443)
###############################################################################

set -e

# Configuration
SERVER_IP="46.224.115.100"
SERVER_USER="root"
DOMAIN="marketing.brianborncamp.com"
APP_DIR="/opt/marketing-tracker"
EMAIL="admin@brianborncamp.com"  # For Let's Encrypt notifications

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     Marketing Campaign Tracker - Production Deployment        ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
log_info "Domain: ${DOMAIN}"
log_info "Server: ${SERVER_IP}"
log_info "SSL: Let's Encrypt (auto-renewal enabled)"
echo ""

# Check if .env file exists (now optional with onboarding flow)
if [ ! -f .env ]; then
    log_warn ".env file not found - will use automated onboarding flow"
    log_info "After deployment, open the app in your browser to configure credentials"

    # Create a minimal .env file for the backend to start
    cat > .env << 'ENVEOF'
# Minimal config - credentials will be set via onboarding flow
API_HOST=0.0.0.0
API_PORT=8000
API_CORS_ORIGINS=https://marketing.brianborncamp.com,http://marketing.brianborncamp.com,http://localhost:3000
ENVEOF
    log_info "✓ Created minimal .env file"
else
    log_info "✓ Using existing .env file"
fi

log_info "Starting deployment..."

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
           ./ ${SERVER_USER}@${SERVER_IP}:${APP_DIR}/ > /dev/null

log_info "✓ Files copied"

# Copy environment file
log_info "Copying environment configuration..."
scp .env ${SERVER_USER}@${SERVER_IP}:${APP_DIR}/.env > /dev/null

# Update CORS for production domain
ssh ${SERVER_USER}@${SERVER_IP} bash << ENDSSH
    cd ${APP_DIR}
    if grep -q "API_CORS_ORIGINS" .env; then
        sed -i 's|API_CORS_ORIGINS=.*|API_CORS_ORIGINS=https://marketing.brianborncamp.com,http://marketing.brianborncamp.com,http://localhost:3000|' .env
    else
        echo "API_CORS_ORIGINS=https://marketing.brianborncamp.com,http://marketing.brianborncamp.com,http://localhost:3000" >> .env
    fi
ENDSSH

log_info "✓ Configuration updated"

# Deploy containers
log_info "Building and starting containers..."
ssh ${SERVER_USER}@${SERVER_IP} bash << 'ENDSSH'
    cd /opt/marketing-tracker
    docker-compose down 2>/dev/null || true
    docker-compose up -d --build
    sleep 5
    docker-compose ps
ENDSSH

log_info "✓ Containers started"

# Setup Nginx and SSL
log_info "Configuring Nginx reverse proxy with SSL..."

ssh ${SERVER_USER}@${SERVER_IP} bash << 'ENDSSH'
DOMAIN="marketing.brianborncamp.com"
EMAIL="admin@brianborncamp.com"

# Install certbot if needed
if ! command -v certbot &> /dev/null; then
    echo "Installing certbot..."
    apt update > /dev/null 2>&1
    apt install -y certbot python3-certbot-nginx > /dev/null 2>&1
fi

# Create temporary HTTP-only Nginx config for cert generation
cat > /etc/nginx/sites-available/marketing << 'NGINX_EOF'
server {
    listen 80;
    listen [::]:80;
    server_name marketing.brianborncamp.com;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }
}
NGINX_EOF

mkdir -p /var/www/certbot

# Enable site and reload
ln -sf /etc/nginx/sites-available/marketing /etc/nginx/sites-enabled/marketing
nginx -t && systemctl reload nginx

# Get SSL certificate if not exists
if [ ! -d "/etc/letsencrypt/live/${DOMAIN}" ]; then
    echo "Requesting SSL certificate..."
    certbot certonly --nginx -d ${DOMAIN} --non-interactive --agree-tos --email ${EMAIL}
fi

# Now create full config with SSL
cat > /etc/nginx/sites-available/marketing << 'NGINX_EOF'
server {
    listen 80;
    listen [::]:80;
    server_name marketing.brianborncamp.com;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name marketing.brianborncamp.com;

    ssl_certificate /etc/letsencrypt/live/marketing.brianborncamp.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/marketing.brianborncamp.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    access_log /var/log/nginx/marketing.access.log;
    error_log /var/log/nginx/marketing.error.log;

    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://localhost:8000;
    }

    location /docs {
        proxy_pass http://localhost:8000;
    }

    location /openapi.json {
        proxy_pass http://localhost:8000;
    }

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
}
NGINX_EOF

# Reload with SSL config
nginx -t && systemctl reload nginx

# Enable auto-renewal
systemctl enable certbot.timer 2>/dev/null || true
systemctl start certbot.timer 2>/dev/null || true

echo "✓ Nginx configured with SSL"
ENDSSH

log_info "✓ Nginx and SSL configured"

# Verify deployment
sleep 3
log_info "Verifying deployment..."

if ssh ${SERVER_USER}@${SERVER_IP} "docker-compose -f ${APP_DIR}/docker-compose.yml ps | grep -q Up"; then
    log_info "✓ Containers are running"
else
    log_error "Containers failed to start"
    ssh ${SERVER_USER}@${SERVER_IP} "cd ${APP_DIR} && docker-compose logs"
    exit 1
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                  Deployment Complete! 🎉                       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
log_info "✅ Your application is live at:"
echo ""
echo "   🌐  https://marketing.brianborncamp.com"
echo "   📊  https://marketing.brianborncamp.com/docs (API)"
echo ""
log_info "✅ SSL Certificate: Active (auto-renews)"
log_info "✅ HTTP → HTTPS: Automatic redirect"
log_info "✅ Ports: 80 (HTTP) + 443 (HTTPS)"
echo ""
log_info "Next Steps:"
echo "   1. Open https://marketing.brianborncamp.com"
echo "   2. Complete the onboarding wizard"
echo "   3. Start monitoring your campaigns!"
echo ""
log_info "Management Commands:"
echo "   View logs:    ./server-manage.sh logs"
echo "   Restart:      ./server-manage.sh restart"
echo "   SSH to server: ./server-manage.sh ssh"
echo ""
