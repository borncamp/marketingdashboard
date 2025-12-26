#!/bin/bash

###############################################################################
# Nginx SSL Setup Script for Marketing Campaign Tracker
# Sets up Nginx reverse proxy with Let's Encrypt SSL
###############################################################################

set -e

SERVER_IP="46.224.115.100"
SERVER_USER="root"
DOMAIN="marketing.brianborncamp.com"
APP_DIR="/opt/marketing-tracker"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

log_info "Setting up Nginx reverse proxy with SSL for ${DOMAIN}..."

# Create Nginx configuration
log_info "Creating Nginx configuration on server..."

ssh ${SERVER_USER}@${SERVER_IP} bash << 'ENDSSH'
DOMAIN="marketing.brianborncamp.com"

# Create Nginx config
cat > /etc/nginx/sites-available/marketing << 'NGINX_EOF'
# Marketing Campaign Tracker - Nginx Configuration

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name marketing.brianborncamp.com;

    # Allow Let's Encrypt challenges
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name marketing.brianborncamp.com;

    # SSL certificates (will be added by certbot)
    ssl_certificate /etc/letsencrypt/live/marketing.brianborncamp.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/marketing.brianborncamp.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/marketing.access.log;
    error_log /var/log/nginx/marketing.error.log;

    # Backend API - proxy to port 8000
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check
    location /health {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    # API docs
    location /docs {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    location /openapi.json {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    # Frontend - proxy to port 3000
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/javascript application/json image/svg+xml;
}
NGINX_EOF

# Create certbot directory
mkdir -p /var/www/certbot

# Enable the site
ln -sf /etc/nginx/sites-available/marketing /etc/nginx/sites-enabled/marketing

# Test Nginx configuration
nginx -t

# Reload Nginx
systemctl reload nginx

echo "✓ Nginx configuration created and enabled"
ENDSSH

log_info "✓ Nginx configuration created"

# Install Certbot if needed and get SSL certificate
log_info "Setting up SSL certificate with Let's Encrypt..."

ssh ${SERVER_USER}@${SERVER_IP} bash << 'ENDSSH'
DOMAIN="marketing.brianborncamp.com"

# Install certbot if not present
if ! command -v certbot &> /dev/null; then
    echo "Installing certbot..."
    apt update
    apt install -y certbot python3-certbot-nginx
fi

# Get SSL certificate
echo "Requesting SSL certificate for ${DOMAIN}..."

# First, temporarily disable SSL in nginx to get initial cert
sed -i 's/listen 443 ssl/listen 443/g' /etc/nginx/sites-available/marketing
sed -i 's/ssl_certificate/#ssl_certificate/g' /etc/nginx/sites-available/marketing
systemctl reload nginx

# Request certificate
certbot certonly --nginx -d ${DOMAIN} --non-interactive --agree-tos --email admin@brianborncamp.com || {
    echo "Certbot failed, trying webroot method..."
    certbot certonly --webroot -w /var/www/certbot -d ${DOMAIN} --non-interactive --agree-tos --email admin@brianborncamp.com
}

# Restore SSL configuration
sed -i 's/listen 443/listen 443 ssl/g' /etc/nginx/sites-available/marketing
sed -i 's/#ssl_certificate/ssl_certificate/g' /etc/nginx/sites-available/marketing
systemctl reload nginx

# Set up auto-renewal
systemctl enable certbot.timer
systemctl start certbot.timer

echo "✓ SSL certificate installed and auto-renewal configured"
ENDSSH

log_info "✓ SSL certificate installed"

log_info "=========================================="
log_info "Nginx SSL Setup Complete!"
log_info "=========================================="
log_info ""
log_info "Your site will be accessible at:"
log_info "  https://marketing.brianborncamp.com"
log_info ""
log_info "Backend API will be at:"
log_info "  https://marketing.brianborncamp.com/api"
log_info "  https://marketing.brianborncamp.com/docs"
log_info ""
log_info "SSL certificate will auto-renew via certbot timer"
log_info ""
