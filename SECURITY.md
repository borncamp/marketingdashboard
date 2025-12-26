# Security & Secrets Management

## 🔒 Git Ignore Protection

This project is configured to **prevent sensitive files from being committed to git**.

### Protected Files

The following files and patterns are **automatically ignored** by git:

#### Environment Variables
- `.env` (all .env files in any directory)
- `.env.local`
- `.env.production`
- `.env.development`
- `backend/.env`
- `frontend/.env`
- Any file ending in `.env`

**Exception:** `.env.example` files ARE tracked (they're templates without secrets)

#### Credentials & Secrets
- `*credentials*` (any file with "credentials" in the name)
- `*secret*` (any file with "secret" in the name)
- API key files
- Authentication tokens

**Exception:** `check-secrets.sh` script IS tracked (it's a security tool)

#### SSL Certificates & Keys
- `*.pem` (certificate files)
- `*.key` (private keys)
- `*.crt` (certificates)
- `*.csr` (certificate signing requests)
- `acme.json` (Let's Encrypt certificates)
- `traefik/acme.json`

#### Backup Files
- `backup/` directory and all contents
- `*.backup` files
- `*.bak` files

#### Other Protected Files
- `poetry.lock` (to avoid version conflicts)
- Python bytecode (`__pycache__/`, `*.pyc`)
- Node modules (`node_modules/`)
- Build artifacts (`dist/`, `build/`)
- IDE settings (`.vscode/`, `.idea/`)

## ✅ Security Verification

### Run Security Check

Before committing, verify no secrets will be exposed:

```bash
./check-secrets.sh
```

This script will:
- ✓ Check if sensitive files would be committed
- ✓ Verify .env files are ignored
- ✓ Confirm .env.example files ARE tracked
- ✓ Validate SSL certificates are protected
- ✓ Ensure backup files are ignored

Expected output:
```
✅ Security check PASSED

Safe to commit:
  • .env files are ignored
  • .env.example files are tracked
  • Secrets and credentials are protected
  • SSL certificates are ignored
  • Backup files are ignored
```

### Manual Verification

Check what will be committed:

```bash
# See what files are staged
git status

# See exactly what would be committed
git diff --cached

# Dry-run to see what would be added
git add -n .
```

## 🚨 Never Commit These

**NEVER commit files containing:**

1. **Google Ads API credentials**
   - Developer tokens
   - Client IDs / Client secrets
   - Refresh tokens
   - Customer IDs (if in plaintext)

2. **Server credentials**
   - SSH keys
   - SSL certificates
   - Private keys
   - Database passwords

3. **API keys and tokens**
   - Meta Ads tokens
   - Reddit Ads credentials
   - Any third-party API keys

4. **Environment-specific configs**
   - Production `.env` files
   - Server-specific settings
   - Email credentials

## ✅ Safe to Commit

These files ARE safe and SHOULD be committed:

1. **Template files**
   - `.env.example`
   - `backend/.env.example`
   - `frontend/.env.example`

2. **Documentation**
   - README.md
   - DEPLOYMENT.md
   - This SECURITY.md file

3. **Scripts**
   - `deploy-simple.sh`
   - `deploy.sh`
   - `server-manage.sh`
   - `check-secrets.sh`

4. **Configuration templates**
   - `nginx-ssl.conf`
   - `docker-compose.yml`

## 🔐 Best Practices

### 1. Use Environment Variables

Always store secrets in `.env` files, never hardcode them:

**❌ Bad:**
```python
GOOGLE_ADS_TOKEN = "your_actual_token_here"
```

**✅ Good:**
```python
from app.config import settings
token = settings.google_ads_developer_token
```

### 2. Keep .env.example Updated

When adding new environment variables:

1. Add to `.env` with the actual value
2. Add to `.env.example` with a placeholder:

```bash
# .env (not committed)
GOOGLE_ADS_DEVELOPER_TOKEN=abc123real_token

# .env.example (committed)
GOOGLE_ADS_DEVELOPER_TOKEN=your_developer_token_here
```

### 3. Review Before Committing

Always run before committing:

```bash
# Check what will be committed
git status

# Run security check
./check-secrets.sh

# Review the actual changes
git diff
```

### 4. Rotate Compromised Credentials

If you accidentally commit secrets:

1. **Immediately revoke** the compromised credentials
2. **Generate new** credentials
3. **Update** `.env` file
4. **Rewrite git history** (if needed):
   ```bash
   # Remove file from git history (advanced)
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch path/to/file" \
     --prune-empty --tag-name-filter cat -- --all
   ```
5. **Force push** (if already pushed):
   ```bash
   git push --force --all
   ```

## 📋 Deployment Security

### Server-Side Secrets

When deploying:

1. **Never commit** the production `.env` to git
2. **Copy directly** to server:
   ```bash
   scp .env root@46.224.115.100:/opt/marketing-tracker/.env
   ```
3. **Set proper permissions** on server:
   ```bash
   ssh root@46.224.115.100 'chmod 600 /opt/marketing-tracker/.env'
   ```

### Backup Security

When backing up:

1. Backups may contain secrets - protect them
2. Use the script:
   ```bash
   ./server-manage.sh backup
   ```
3. Store backups securely (not in git):
   ```bash
   # Backups go to ./backup/ which is gitignored
   ls ./backup/
   ```

## 🔍 Audit Trail

### Check Git History for Secrets

Scan git history for accidentally committed secrets:

```bash
# Search for common secret patterns
git log -p | grep -i "secret\|password\|token\|key"

# Check for .env files in history
git log --all --full-history -- "*.env"
```

### Use Git Hooks (Optional)

Prevent accidental commits with pre-commit hook:

```bash
# Create pre-commit hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
if ./check-secrets.sh; then
    exit 0
else
    echo "❌ Security check failed - commit blocked"
    exit 1
fi
EOF

chmod +x .git/hooks/pre-commit
```

## 📞 If Secrets Are Compromised

1. **Don't panic** - but act quickly
2. **Revoke immediately** - disable the compromised credentials
3. **Generate new** - create fresh credentials
4. **Update everywhere** - server, local, team members
5. **Review access** - check if unauthorized access occurred
6. **Document** - record what happened and how it was fixed

## ✅ Security Checklist

Before each deployment:

- [ ] `.env` file contains actual secrets (not committed)
- [ ] `.env.example` has placeholders (is committed)
- [ ] Run `./check-secrets.sh` - passes
- [ ] No sensitive files in `git status`
- [ ] SSL certificates not in repo
- [ ] Backup directory is gitignored
- [ ] Server `.env` permissions are `600`
- [ ] All team members use their own credentials

## 🎯 Summary

**Remember:**
- ✅ Templates (.env.example) → **Commit**
- ❌ Actual secrets (.env) → **Never commit**
- ✅ Scripts and docs → **Commit**
- ❌ Credentials and keys → **Never commit**
- ✅ Use `check-secrets.sh` → **Always run before commit**

Stay secure! 🔒
