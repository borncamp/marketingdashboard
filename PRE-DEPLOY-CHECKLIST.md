# Pre-Deployment Checklist

Before deploying to **marketing.brianborncamp.com** (46.224.115.100), complete this checklist:

## 1. Local Setup ✓

- [ ] Project files are complete
- [ ] All scripts are executable (`chmod +x *.sh`)
- [ ] `.env` file is created and configured
- [ ] `.env` contains valid Google Ads API credentials

### Verify .env File

Your `.env` should contain:
```bash
GOOGLE_ADS_DEVELOPER_TOKEN=your_token
GOOGLE_ADS_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_ADS_CLIENT_SECRET=your_secret
GOOGLE_ADS_REFRESH_TOKEN=your_refresh_token
GOOGLE_ADS_CUSTOMER_ID=1234567890  # No hyphens!
```

Test locally if possible:
```bash
cd backend
poetry install
poetry run python -m app.main
# Should start without errors
```

## 2. Google Ads API Setup ✓

- [ ] Google Cloud Project created
- [ ] Google Ads API enabled
- [ ] OAuth 2.0 credentials generated
- [ ] Developer token obtained (or using test account)
- [ ] Refresh token generated
- [ ] Customer ID identified (10 digits, no hyphens)
- [ ] Test account has active campaigns with data

### Test API Access

```bash
# Quick test script
cd backend
poetry run python << EOF
from app.services import GoogleAdsAdapter
import asyncio

async def test():
    adapter = GoogleAdsAdapter()
    campaigns = await adapter.get_campaigns()
    print(f"Found {len(campaigns)} campaigns")

asyncio.run(test())
EOF
```

## 3. Server Access ✓

- [ ] SSH key configured for root@46.224.115.100
- [ ] Can successfully SSH to server
- [ ] Server has sufficient resources (2GB+ RAM recommended)

### Test SSH Connection

```bash
ssh root@46.224.115.100 "echo 'SSH connection works!'"
```

## 4. DNS Configuration ✓

- [ ] A record created: `marketing.brianborncamp.com` → `46.224.115.100`
- [ ] DNS propagation complete (check with `dig marketing.brianborncamp.com`)

### Verify DNS

```bash
# Check DNS resolution
dig marketing.brianborncamp.com +short
# Should return: 46.224.115.100

# Or use nslookup
nslookup marketing.brianborncamp.com
```

## 5. Choose Deployment Method ✓

Select ONE deployment method:

### Option A: Simple Deployment (Quick Start)
- No SSL initially
- Direct port access
- Good for testing
- **Command:** `./deploy-simple.sh`

### Option B: Production with Traefik (Automatic SSL)
- Automatic SSL certificates
- Reverse proxy included
- Production-ready
- **Command:** `./deploy.sh`

### Option C: Manual Nginx Setup (Most Control)
- Full control over configuration
- Manual SSL setup with Certbot
- Custom Nginx config
- **Follow:** [DEPLOYMENT.md](DEPLOYMENT.md) - Option 3

**Recommended for production:** Option B or C

## 6. Firewall Configuration ✓

Ensure these ports are accessible:

- [ ] Port 22 (SSH) - Already working
- [ ] Port 80 (HTTP) - For Let's Encrypt validation
- [ ] Port 443 (HTTPS) - For HTTPS traffic
- [ ] Port 3000 (Frontend) - If using simple deploy
- [ ] Port 8000 (Backend) - If using simple deploy

### Configure UFW on Server

```bash
ssh root@46.224.115.100 << 'ENDSSH'
    apt install -y ufw
    ufw allow ssh
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw allow 3000/tcp
    ufw allow 8000/tcp
    ufw --force enable
    ufw status
ENDSSH
```

## 7. Pre-Deployment Test ✓

Run a final check:

```bash
# 1. Check .env exists
if [ ! -f .env ]; then
    echo "❌ .env file missing!"
else
    echo "✓ .env file exists"
fi

# 2. Check SSH
if ssh -o ConnectTimeout=5 root@46.224.115.100 "echo 'OK'" > /dev/null 2>&1; then
    echo "✓ SSH connection works"
else
    echo "❌ SSH connection failed"
fi

# 3. Check DNS
if dig +short marketing.brianborncamp.com | grep -q "46.224.115.100"; then
    echo "✓ DNS configured correctly"
else
    echo "⚠ DNS not propagated yet"
fi

# 4. Check scripts are executable
if [ -x deploy-simple.sh ]; then
    echo "✓ Deploy scripts are executable"
else
    echo "❌ Scripts not executable - run: chmod +x *.sh"
fi
```

## 8. Ready to Deploy! 🚀

If all checks pass, you're ready to deploy:

### For Simple Deployment:
```bash
./deploy-simple.sh
```

### For Production with SSL:
```bash
./deploy.sh
```

### Watch the deployment:
The script will:
1. ✓ Install Docker on server
2. ✓ Copy application files
3. ✓ Build Docker containers
4. ✓ Start services
5. ✓ Verify deployment

## 9. Post-Deployment Verification ✓

After deployment completes:

### Check Services
```bash
./server-manage.sh status
```

### View Logs
```bash
./server-manage.sh logs
```

### Test Health
```bash
./server-manage.sh health
```

### Access Application

**Simple Deploy:**
- Frontend: http://46.224.115.100:3000
- Backend: http://46.224.115.100:8000/docs

**With SSL:**
- Application: https://marketing.brianborncamp.com
- API Docs: https://marketing.brianborncamp.com/api/docs

## 10. Troubleshooting ✓

If deployment fails:

### Check Logs
```bash
./server-manage.sh logs
```

### Common Issues

**"Cannot connect to server"**
- Verify SSH key is loaded: `ssh-add -l`
- Test connection: `ssh root@46.224.115.100`

**"Failed to load campaigns"**
- Check .env credentials
- View backend logs: `./server-manage.sh logs-f`
- Verify Google Ads API access

**"Containers won't start"**
- Check Docker logs: `./server-manage.sh logs`
- Rebuild: `./server-manage.sh rebuild`

**"DNS not resolving"**
- Wait for DNS propagation (can take up to 24 hours)
- Use IP address temporarily: http://46.224.115.100:3000

## Quick Reference

### Deployment Scripts
- `./deploy-simple.sh` - Simple deployment without SSL
- `./deploy.sh` - Production deployment with Traefik SSL
- `./server-manage.sh [command]` - Server management commands

### Management Commands
```bash
./server-manage.sh status      # Container status
./server-manage.sh logs        # View logs
./server-manage.sh logs-f      # Follow logs
./server-manage.sh restart     # Restart all
./server-manage.sh health      # Health check
./server-manage.sh ssh         # SSH to server
```

### Documentation
- [README.md](README.md) - Application documentation
- [QUICKSTART.md](QUICKSTART.md) - Quick start guide
- [DEPLOYMENT.md](DEPLOYMENT.md) - Detailed deployment guide

---

## Ready? Let's Deploy! 🎯

```bash
# Final check
./server-manage.sh health

# Deploy!
./deploy-simple.sh

# Watch it work
./server-manage.sh logs-f
```

Good luck! 🚀
