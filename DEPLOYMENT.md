# Deployment Guide for marketing.brianborncamp.com

This guide covers deploying the Marketing Campaign Tracker to your VPS at **46.224.115.100** with the domain **marketing.brianborncamp.com**.

## Quick Deploy (Recommended)

```bash
# 1. Ensure you have SSH access
ssh root@46.224.115.100

# 2. Make sure your .env file is configured
cp .env.example .env
# Edit .env with your Google Ads API credentials

# 3. Run the deployment script
./deploy-simple.sh
```

## Pre-Deployment Checklist

- [ ] SSH key configured for `root@46.224.115.100`
- [ ] `.env` file created with Google Ads API credentials
- [ ] DNS A record: `marketing.brianborncamp.com` → `46.224.115.100`
- [ ] Firewall allows ports 80, 443, 3000, 8000
- [ ] Docker and Docker Compose will be installed automatically

## Deployment Options

### Option 1: Simple Deployment (No SSL)

Use this for quick testing or if you'll set up SSL manually later.

```bash
./deploy-simple.sh
```

**Access:**
- Frontend: http://46.224.115.100:3000
- Backend API: http://46.224.115.100:8000/docs

### Option 2: Production Deployment with Traefik (SSL)

Use this for production with automatic SSL certificates.

```bash
./deploy.sh
```

**Features:**
- Automatic SSL certificates from Let's Encrypt
- HTTPS redirect
- Reverse proxy with Traefik

**Access:**
- https://marketing.brianborncamp.com

### Option 3: Manual Nginx Setup (Most Control)

For full control over your reverse proxy setup.

#### Step 1: Deploy the application

```bash
./deploy-simple.sh
```

#### Step 2: Install Nginx and Certbot on the server

```bash
ssh root@46.224.115.100

# Install Nginx
apt update
apt install -y nginx

# Install Certbot
apt install -y certbot python3-certbot-nginx

# Enable and start Nginx
systemctl enable nginx
systemctl start nginx
```

#### Step 3: Configure Nginx

```bash
# Copy the nginx configuration
scp nginx-ssl.conf root@46.224.115.100:/etc/nginx/sites-available/marketing

# On the server, create symlink
ssh root@46.224.115.100
ln -s /etc/nginx/sites-available/marketing /etc/nginx/sites-enabled/
nginx -t  # Test configuration
systemctl reload nginx
```

#### Step 4: Get SSL Certificate

```bash
# On the server
certbot --nginx -d marketing.brianborncamp.com

# Follow the prompts
# - Enter your email
# - Agree to terms
# - Choose to redirect HTTP to HTTPS (recommended)
```

#### Step 5: Set up auto-renewal

```bash
# Test renewal
certbot renew --dry-run

# Certbot automatically sets up a systemd timer for renewal
systemctl status certbot.timer
```

## DNS Configuration

Before deploying, ensure your DNS is configured:

```
Type: A
Name: marketing
Value: 46.224.115.100
TTL: 3600 (or Auto)
```

Full domain: `marketing.brianborncamp.com` → `46.224.115.100`

## Firewall Configuration

On your VPS, configure the firewall to allow necessary ports:

```bash
ssh root@46.224.115.100

# Install UFW if not present
apt install -y ufw

# Configure firewall
ufw allow ssh
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 3000/tcp  # Frontend (if using simple deploy)
ufw allow 8000/tcp  # Backend API (if using simple deploy)

# Enable firewall
ufw --force enable

# Check status
ufw status
```

## Post-Deployment Verification

### 1. Check Container Status

```bash
ssh root@46.224.115.100
cd /opt/marketing-tracker
docker-compose ps
```

Expected output:
```
NAME                      STATUS    PORTS
marketing-tracker-backend  Up       0.0.0.0:8000->8000/tcp
marketing-tracker-frontend Up       0.0.0.0:3000->80/tcp
```

### 2. Check Logs

```bash
# All logs
docker-compose logs

# Backend only
docker-compose logs backend

# Frontend only
docker-compose logs frontend

# Follow logs in real-time
docker-compose logs -f
```

### 3. Test Endpoints

```bash
# Health check
curl http://46.224.115.100:8000/health

# API documentation
curl http://46.224.115.100:8000/docs

# Frontend
curl http://46.224.115.100:3000
```

### 4. Test in Browser

Visit:
- http://marketing.brianborncamp.com:3000 (simple deploy)
- https://marketing.brianborncamp.com (with SSL)

You should see the campaign dashboard.

## Updating the Application

### Update Code

```bash
# On your local machine
# Make your changes, then redeploy
./deploy-simple.sh
```

### Update Environment Variables

```bash
# Edit .env locally
vim .env

# Copy to server
scp .env root@46.224.115.100:/opt/marketing-tracker/.env

# Restart containers
ssh root@46.224.115.100 'cd /opt/marketing-tracker && docker-compose restart'
```

### Update Dependencies

```bash
# Backend dependencies (Poetry)
# Edit backend/pyproject.toml locally, then redeploy
./deploy-simple.sh

# Frontend dependencies (npm)
# Edit frontend/package.json locally, then redeploy
./deploy-simple.sh
```

## Maintenance Commands

### View Logs

```bash
ssh root@46.224.115.100 'cd /opt/marketing-tracker && docker-compose logs -f'
```

### Restart Services

```bash
# Restart all
ssh root@46.224.115.100 'cd /opt/marketing-tracker && docker-compose restart'

# Restart backend only
ssh root@46.224.115.100 'cd /opt/marketing-tracker && docker-compose restart backend'

# Restart frontend only
ssh root@46.224.115.100 'cd /opt/marketing-tracker && docker-compose restart frontend'
```

### Stop Services

```bash
ssh root@46.224.115.100 'cd /opt/marketing-tracker && docker-compose down'
```

### Start Services

```bash
ssh root@46.224.115.100 'cd /opt/marketing-tracker && docker-compose up -d'
```

### Clean Up Old Docker Images

```bash
ssh root@46.224.115.100 'docker system prune -a'
```

## Monitoring

### Check Resource Usage

```bash
ssh root@46.224.115.100

# Docker container stats
docker stats

# Disk usage
df -h

# Memory usage
free -h

# CPU load
top
```

### Set Up Log Rotation

```bash
ssh root@46.224.115.100

# Create log rotation config
cat > /etc/logrotate.d/docker-compose << EOF
/opt/marketing-tracker/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
EOF
```

## Troubleshooting

### Containers Won't Start

```bash
# Check logs
ssh root@46.224.115.100 'cd /opt/marketing-tracker && docker-compose logs'

# Check .env file
ssh root@46.224.115.100 'cat /opt/marketing-tracker/.env'

# Rebuild containers
ssh root@46.224.115.100 'cd /opt/marketing-tracker && docker-compose down && docker-compose up -d --build'
```

### "Failed to fetch campaigns" Error

1. Check Google Ads API credentials in `.env`
2. Verify refresh token is still valid
3. Check backend logs: `docker-compose logs backend`
4. Ensure customer ID is correct (no hyphens)

### SSL Certificate Issues

```bash
# Renew certificates manually
ssh root@46.224.115.100
certbot renew --force-renewal

# Check certificate expiry
certbot certificates
```

### Port Already in Use

```bash
# Find what's using the port
ssh root@46.224.115.100
lsof -i :3000
lsof -i :8000

# Kill the process or change docker-compose ports
```

## Backup and Recovery

### Backup Configuration

```bash
# Backup .env file
scp root@46.224.115.100:/opt/marketing-tracker/.env ./backup/.env.backup

# Backup entire app directory
ssh root@46.224.115.100 'tar -czf /tmp/marketing-backup.tar.gz /opt/marketing-tracker'
scp root@46.224.115.100:/tmp/marketing-backup.tar.gz ./backup/
```

### Restore from Backup

```bash
# Restore .env
scp ./backup/.env.backup root@46.224.115.100:/opt/marketing-tracker/.env

# Restart services
ssh root@46.224.115.100 'cd /opt/marketing-tracker && docker-compose restart'
```

## Security Best Practices

1. **Use environment variables** - Never commit `.env` to git
2. **Keep Docker updated** - Regularly update Docker and images
3. **Enable firewall** - Only open necessary ports
4. **Use SSL** - Always use HTTPS in production
5. **Regular backups** - Back up `.env` and configuration
6. **Monitor logs** - Check for suspicious activity
7. **Update dependencies** - Keep Python and npm packages updated

## Support

If you encounter issues:

1. Check the logs: `docker-compose logs`
2. Verify DNS is propagated: `dig marketing.brianborncamp.com`
3. Test connectivity: `curl -I http://46.224.115.100:8000/health`
4. Review this deployment guide
5. Check the main [README.md](README.md) for application-specific issues

---

**Server Details:**
- IP: 46.224.115.100
- Domain: marketing.brianborncamp.com
- User: root
- App Directory: /opt/marketing-tracker
- Ports: 80 (HTTP), 443 (HTTPS), 3000 (Frontend), 8000 (Backend)
