# Password Management Guide

This application uses HTTP Basic Authentication to protect your marketing dashboard. Credentials are stored in the `.env` file, which is **never committed to git**.

## Quick Reference

### Local Development

Change password on your local machine:
```bash
./set-password.sh
```

Then restart the backend:
```bash
docker-compose restart backend
```

### Production Server

Change password on the remote server from your local machine:
```bash
./set-remote-password.sh
```

This script will:
1. Prompt for new username and password
2. SSH to your production server
3. Update the `.env` file
4. Restart the backend container
5. Verify the backend is healthy

### Manual Password Update

If you prefer to update manually:

1. **Edit `.env` file**
   ```bash
   # On local machine
   nano .env

   # Or on remote server
   ssh root@46.224.115.100
   cd /opt/marketing-tracker
   nano .env
   ```

2. **Update these lines**
   ```
   AUTH_USERNAME=your_username
   AUTH_PASSWORD=your_secure_password
   ```

3. **Restart backend**
   ```bash
   docker-compose restart backend
   ```

## Security Best Practices

✅ **DO:**
- Use strong passwords (8+ characters, mix of letters, numbers, symbols)
- Change default password immediately after deployment
- Rotate passwords regularly (every 90 days recommended)
- Use `set-password.sh` or `set-remote-password.sh` scripts
- Keep `.env` file permissions restricted (600 or 640)

❌ **DON'T:**
- Commit `.env` file to git (already in `.gitignore`)
- Share passwords via email or chat
- Use the default `admin/admin` credentials in production
- Store passwords in code or documentation

## How It Works

### Authentication Flow
1. User visits the application
2. Browser shows native HTTP Basic Auth dialog
3. User enters username and password
4. Backend validates credentials using constant-time comparison
5. If valid, user accesses the dashboard

### Storage
- Passwords are stored in **plain text** in `.env` file
- `.env` file is protected by file system permissions
- `.env` file is **never committed** to version control
- HTTP transmission is protected by HTTPS (in production)

### Why Plain Text?
This is a single-user dashboard with simple authentication needs:
- No user database or multi-user support needed
- Simpler than JWT/OAuth/bcrypt complexity
- Suitable for personal use with proper file permissions
- HTTPS encrypts credentials in transit
- Alternative: upgrade to a full auth system if needed

## Troubleshooting

### "Incorrect username or password" error

1. **Check `.env` file**
   ```bash
   cat .env | grep AUTH_
   ```

2. **Verify backend loaded the credentials**
   ```bash
   docker-compose logs backend | grep -i auth
   ```

3. **Try updating password again**
   ```bash
   ./set-password.sh
   docker-compose restart backend
   ```

### Password script fails

1. **Make scripts executable**
   ```bash
   chmod +x set-password.sh set-remote-password.sh
   ```

2. **Check `.env` file exists**
   ```bash
   ls -la .env
   # If missing, copy from example
   cp .env.example .env
   ```

### Browser keeps showing old password

1. **Clear browser's HTTP Basic Auth cache**
   - Close all browser tabs for the site
   - Clear browser cookies/cache
   - Or use incognito/private browsing mode

2. **Verify new password is set**
   ```bash
   curl -u newuser:newpass http://localhost:8000/health
   ```

## Advanced: Environment Variables

Instead of storing in `.env` file, you can set as environment variables:

```bash
# In docker-compose.yml
environment:
  - AUTH_USERNAME=myuser
  - AUTH_PASSWORD=mysecretpass
```

Or export before running:
```bash
export AUTH_USERNAME=myuser
export AUTH_PASSWORD=mysecretpass
docker-compose up
```

## Upgrade to More Secure Auth

If you need more advanced authentication:

1. **OAuth2/OIDC** - Use external identity provider (Google, GitHub, etc.)
2. **JWT tokens** - Stateless token-based auth
3. **bcrypt hashing** - Store password hashes instead of plain text
4. **Multi-user support** - Database with user accounts

Let me know if you need help implementing any of these!
