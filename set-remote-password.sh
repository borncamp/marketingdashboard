#!/bin/bash
# Set password on remote production server
# Usage: ./set-remote-password.sh

set -e

REMOTE_HOST="root@46.224.115.100"
REMOTE_DIR="/opt/marketing-tracker"

echo "=== Remote Password Manager ==="
echo "Server: $REMOTE_HOST"
echo

# Get username
read -p "Enter username (default: admin): " USERNAME
USERNAME=${USERNAME:-admin}

# Get password
read -sp "Enter new password: " PASSWORD
echo
read -sp "Confirm password: " PASSWORD_CONFIRM
echo

if [ "$PASSWORD" != "$PASSWORD_CONFIRM" ]; then
    echo "❌ Passwords don't match!"
    exit 1
fi

# Validate password
if [ ${#PASSWORD} -lt 8 ]; then
    echo "⚠️  Warning: Password is less than 8 characters"
    read -p "Continue anyway? (y/N): " CONTINUE
    if [ "$CONTINUE" != "y" ] && [ "$CONTINUE" != "Y" ]; then
        echo "Cancelled."
        exit 1
    fi
fi

echo
echo "Updating credentials on remote server..."

# SSH to server and update .env file
ssh "$REMOTE_HOST" bash <<EOF
set -e
cd "$REMOTE_DIR"

# Backup .env
cp .env .env.backup.\$(date +%Y%m%d_%H%M%S)

# Update credentials
if grep -q "^AUTH_USERNAME=" .env; then
    sed -i "s|^AUTH_USERNAME=.*|AUTH_USERNAME=$USERNAME|" .env
else
    echo "AUTH_USERNAME=$USERNAME" >> .env
fi

if grep -q "^AUTH_PASSWORD=" .env; then
    sed -i "s|^AUTH_PASSWORD=.*|AUTH_PASSWORD=$PASSWORD|" .env
else
    echo "AUTH_PASSWORD=$PASSWORD" >> .env
fi

# Restart backend to apply changes
echo "Restarting backend container..."
docker-compose restart backend

echo "Waiting for backend to start..."
sleep 3

# Check if backend is healthy
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Backend is healthy"
else
    echo "⚠️  Backend health check failed - check logs with: docker-compose logs backend"
fi
EOF

echo
echo "✅ Password updated successfully on remote server!"
echo
echo "Username: $USERNAME"
echo "Password: ********"
echo
echo "Test the new credentials:"
echo "  curl -u $USERNAME:****** https://marketing.brianborncamp.com/api/campaigns"
echo
