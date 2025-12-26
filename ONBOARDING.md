# Automated Onboarding Guide

The Marketing Campaign Tracker now features an **automated onboarding flow** that guides you through Google Ads API setup directly in the web interface!

## 🎯 No More Manual .env Editing!

Instead of manually editing `.env` files, you can now:
1. Launch the application
2. Follow the interactive setup wizard
3. Connect your Google Ads account in minutes

## 🚀 Quick Start

### Option 1: Automated Onboarding (Recommended)

```bash
# 1. Deploy the application (no .env needed!)
./deploy-simple.sh

# 2. Open in browser
open http://marketing.brianborncamp.com:3000

# 3. Follow the onboarding wizard
# The app will guide you through each step!
```

That's it! The onboarding flow will:
- ✅ Walk you through getting Google Ads credentials
- ✅ Generate OAuth URLs for you
- ✅ Exchange authorization codes automatically
- ✅ Validate your credentials
- ✅ Save everything encrypted and secure

### Option 2: Manual .env Setup (Still Supported)

If you prefer the traditional approach:

```bash
cp .env.example .env
vim .env  # Add your credentials
./deploy-simple.sh
```

The app will detect existing `.env` credentials and skip onboarding.

## 📱 Onboarding Flow Steps

### Step 1: Welcome
- Introduction to the setup process
- List of requirements
- Links to setup guides

### Step 2: Enter Credentials
Enter your Google Ads API credentials:
- **Developer Token** - From [Google Ads API Center](https://ads.google.com/aw/apicenter)
- **Client ID & Secret** - From [Google Cloud Console](https://console.cloud.google.com/)
- **Customer ID** - Your 10-digit Google Ads account ID

### Step 3: OAuth Authorization
- Click to open Google's authorization page
- Sign in with your Google Ads account
- Grant permissions
- Copy the authorization code
- Paste it back into the wizard

### Step 4: Validation
- The app exchanges the code for a refresh token
- Validates all credentials
- Tests connection to your Google Ads account
- Shows your account name for confirmation

### Step 5: Complete!
- Settings saved encrypted
- Redirects to campaign dashboard
- You're all set!

## 🔐 Security Features

### Encrypted Storage
- All credentials stored encrypted using Fernet (symmetric encryption)
- Encryption key can be set via `SETTINGS_ENCRYPTION_KEY` environment variable
- Default: Generated key (shown in logs on first run)

### No Plain Text Storage
- Credentials never stored in plain text
- Not committed to git
- Encrypted at rest

### Secure Transmission
- All API calls use HTTPS (in production)
- OAuth flow follows Google's best practices
- Refresh tokens used for long-term access

## 🛠️ Advanced Configuration

### Custom Encryption Key

Set a custom encryption key for production:

```bash
# Generate a key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Set in environment
export SETTINGS_ENCRYPTION_KEY="your_generated_key_here"
```

Add to `docker-compose.yml`:
```yaml
services:
  backend:
    environment:
      - SETTINGS_ENCRYPTION_KEY=${SETTINGS_ENCRYPTION_KEY}
```

### Settings Storage Location

By default, settings are stored in `/tmp/marketing-settings.enc`

To customize:
```python
# In backend/app/services/settings_manager.py
settings_manager = SettingsManager(storage_path="/your/custom/path.enc")
```

### API Endpoints

The onboarding flow uses these endpoints:

- `GET /api/settings` - Check if configured
- `POST /api/settings` - Save settings
- `POST /api/settings/validate` - Validate credentials
- `GET /api/settings/oauth-url` - Generate OAuth URL
- `POST /api/settings/exchange-code` - Exchange auth code for refresh token
- `DELETE /api/settings` - Clear saved settings

## 📖 Getting Google Ads Credentials

### 1. Developer Token

1. Go to [Google Ads API Center](https://ads.google.com/aw/apicenter)
2. Sign in with your Google Ads account
3. Apply for a developer token
4. For testing, you can use a test account token immediately
5. For production, wait for approval (can take 24-48 hours)

### 2. OAuth2 Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable "Google Ads API"
4. Go to "Credentials" > "Create Credentials" > "OAuth client ID"
5. Choose "Desktop app" as application type
6. Download JSON or copy Client ID and Client Secret

### 3. Customer ID

1. Log into [Google Ads](https://ads.google.com/)
2. Look for your Customer ID in the top right (10 digits)
3. Remove any hyphens: `123-456-7890` → `1234567890`

## 🔄 Updating Settings

### Via Web Interface

Click the "⚙️ Settings" button in the header to reconfigure:
1. Clears current settings
2. Returns to onboarding flow
3. Walk through setup again

### Via API

```bash
# Clear settings
curl -X DELETE http://localhost:8000/api/settings

# The next page load will show onboarding
```

### Via Server

```bash
# SSH to server
ssh root@46.224.115.100

# Remove settings file
rm /tmp/marketing-settings.enc

# Restart backend
cd /opt/marketing-tracker
docker-compose restart backend
```

## 🐛 Troubleshooting

### "Failed to validate credentials"

**Possible causes:**
- Developer token not approved (use test account)
- Wrong Customer ID
- OAuth credentials incorrect
- Account doesn't have permission

**Solution:**
- Double-check all credentials
- Ensure Customer ID has no hyphens
- Try with a test Google Ads account first

### "Failed to exchange code"

**Possible causes:**
- Authorization code expired (they expire quickly!)
- Code copied incorrectly (extra spaces/newlines)
- Client ID/Secret mismatch

**Solution:**
- Generate a fresh authorization code
- Copy the entire code carefully
- Make sure no extra whitespace

### Settings Not Persisting

**Possible causes:**
- `/tmp` directory cleared on restart
- Docker volume not mounted
- Permissions issue

**Solution:**
```yaml
# Add volume in docker-compose.yml
services:
  backend:
    volumes:
      - ./data:/data
```

```python
# Update storage path
settings_manager = SettingsManager(storage_path="/data/settings.enc")
```

### Can't Access Onboarding Page

**Check:**
1. Backend is running: `./server-manage.sh status`
2. Check logs: `./server-manage.sh logs backend`
3. Settings endpoint works: `curl http://localhost:8000/api/settings`

## 💡 Tips

### For Development
- Use a [Google Ads test account](https://developers.google.com/google-ads/api/docs/first-call/dev-token#test_accounts)
- Test accounts have instant developer token approval
- Create test campaigns to see the dashboard

### For Production
- Apply for production developer token early
- Use a manager account if managing multiple clients
- Set `SETTINGS_ENCRYPTION_KEY` environment variable
- Use persistent storage for settings (not `/tmp`)
- Regular backups of encrypted settings file

### For Teams
- Each team member can use their own Google Ads account
- Or share OAuth credentials (Client ID/Secret)
- Developer token can be shared across team

## 📚 Additional Resources

- [Google Ads API Documentation](https://developers.google.com/google-ads/api/docs/start)
- [OAuth 2.0 Guide](https://developers.google.com/identity/protocols/oauth2)
- [Google Ads Test Accounts](https://developers.google.com/google-ads/api/docs/first-call/dev-token#test_accounts)

## 🎉 Benefits of Automated Onboarding

### For Users
- ✅ No command-line required
- ✅ Step-by-step guidance
- ✅ Visual feedback on each step
- ✅ Instant validation
- ✅ Clear error messages

### For Deployment
- ✅ No `.env` file needed initially
- ✅ Can deploy without credentials
- ✅ Configure after deployment
- ✅ Easy to update settings later

### For Security
- ✅ Encrypted storage
- ✅ Never stored in git
- ✅ API-based configuration
- ✅ Can rotate credentials easily

---

**Ready to get started?** Just deploy the app and open it in your browser - the onboarding wizard will take care of the rest! 🚀
