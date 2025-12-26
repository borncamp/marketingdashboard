# Deploy Quick Start

## 🚀 Deploy in 2 Steps (No .env Required!)

```bash
# Step 1: Deploy
./deploy-simple.sh

# Step 2: Configure via browser
open http://marketing.brianborncamp.com:3000
# Follow the onboarding wizard!
```

That's it! The deployment script now:
- ✅ Works WITHOUT a .env file
- ✅ Creates minimal config automatically
- ✅ Shows onboarding wizard on first visit
- ✅ Guides you through Google Ads setup

## 📋 What Happens

### During Deployment

1. **No .env found?** Script creates minimal config
2. **Copies files** to server via rsync
3. **Builds containers** with Docker Compose
4. **Starts services** - backend on :8000, frontend on :3000

### First Visit to App

1. **Detects no credentials** configured
2. **Shows onboarding wizard** automatically
3. **Guides you through:**
   - Entering Google Ads credentials
   - Authorizing with Google OAuth
   - Validating credentials
   - Saving encrypted settings
4. **Redirects to dashboard** when complete

## 🔄 Alternative: Pre-Configure

If you prefer the old way:

```bash
cp .env.example .env
vim .env  # Add your credentials
./deploy-simple.sh
```

The app detects existing credentials and skips onboarding.

## 🛠️ After Deployment

### Access Your App
- **Frontend:** http://marketing.brianborncamp.com:3000
- **API Docs:** http://marketing.brianborncamp.com:8000/docs
- **Health Check:** http://marketing.brianborncamp.com:8000/health

### Manage Your Deployment
```bash
# View status
./server-manage.sh status

# View logs
./server-manage.sh logs

# Follow logs in real-time
./server-manage.sh logs-f

# Restart services
./server-manage.sh restart

# SSH to server
./server-manage.sh ssh
```

### Update Settings Later
- Click **⚙️ Settings** button in app header
- Or via API: `curl -X DELETE http://your-server:8000/api/settings`

## 📖 Documentation

- **[ONBOARDING.md](ONBOARDING.md)** - Detailed onboarding guide
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Full deployment documentation
- **[README.md](README.md)** - Complete project documentation
- **[SECURITY.md](SECURITY.md)** - Security best practices

## 🎯 Common Scenarios

### Scenario 1: Fresh Deployment (Recommended)
```bash
./deploy-simple.sh
# Open browser, follow wizard
```

### Scenario 2: Deploy with Pre-Configured Credentials
```bash
cp .env.example .env
vim .env  # Add credentials
./deploy-simple.sh
```

### Scenario 3: Redeploy with Updated Code
```bash
./deploy-simple.sh  # Keeps existing settings
```

### Scenario 4: Reset Everything
```bash
./server-manage.sh ssh
rm /tmp/marketing-settings.enc
exit
./deploy-simple.sh
# Onboarding wizard will show again
```

## ✅ Pre-Deployment Checklist

- [ ] SSH key configured for root@46.224.115.100
- [ ] DNS: marketing.brianborncamp.com → 46.224.115.100
- [ ] Firewall allows ports 80, 443, 3000, 8000
- [ ] (Optional) .env file with credentials

## 🐛 Troubleshooting

### Deploy script fails
```bash
# Check SSH
ssh root@46.224.115.100

# Check DNS
dig marketing.brianborncamp.com +short
```

### Can't access app after deploy
```bash
# Check services
./server-manage.sh status

# Check logs
./server-manage.sh logs
```

### Onboarding wizard not showing
```bash
# Check if settings exist
curl http://your-server:8000/api/settings

# Clear settings to show wizard again
curl -X DELETE http://your-server:8000/api/settings
```

## 💡 Pro Tips

1. **No credentials yet?** Deploy anyway! Configure via wizard.
2. **Testing locally first?** Just run `docker-compose up` in the project root.
3. **Multiple environments?** Use different .env files: `.env.prod`, `.env.dev`
4. **Team deployment?** Each member can configure their own credentials via UI.

---

**Ready to deploy?** Just run `./deploy-simple.sh` and you're off! 🎉
