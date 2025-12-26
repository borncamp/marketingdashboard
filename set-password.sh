#!/bin/bash
# Simple password setter for marketing tracker
# Usage: ./set-password.sh [username] [password]
#   OR: ./set-password.sh (interactive mode)

set -e

ENV_FILE=".env"

echo "=== Marketing Tracker Password Manager ==="
echo

# Check if .env exists
if [ ! -f "$ENV_FILE" ]; then
    echo "Creating .env file from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
    else
        touch .env
    fi
fi

# Get username
if [ -n "$1" ]; then
    USERNAME="$1"
else
    read -p "Enter username (default: admin): " USERNAME
    USERNAME=${USERNAME:-admin}
fi

# Get password
if [ -n "$2" ]; then
    PASSWORD="$2"
else
    read -sp "Enter new password: " PASSWORD
    echo
    read -sp "Confirm password: " PASSWORD_CONFIRM
    echo

    if [ "$PASSWORD" != "$PASSWORD_CONFIRM" ]; then
        echo "❌ Passwords don't match!"
        exit 1
    fi
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

# Update or add to .env file
if grep -q "^AUTH_USERNAME=" "$ENV_FILE"; then
    # Use different delimiters for sed to avoid issues with special characters
    sed -i.bak "s|^AUTH_USERNAME=.*|AUTH_USERNAME=$USERNAME|" "$ENV_FILE"
else
    echo "AUTH_USERNAME=$USERNAME" >> "$ENV_FILE"
fi

if grep -q "^AUTH_PASSWORD=" "$ENV_FILE"; then
    sed -i.bak "s|^AUTH_PASSWORD=.*|AUTH_PASSWORD=$PASSWORD|" "$ENV_FILE"
else
    echo "AUTH_PASSWORD=$PASSWORD" >> "$ENV_FILE"
fi

# Clean up backup file
rm -f "${ENV_FILE}.bak"

echo
echo "✅ Credentials updated in .env file"
echo
echo "Username: $USERNAME"
echo "Password: ********"
echo
echo "To apply changes, restart the backend:"
echo "  docker-compose restart backend"
echo
echo "Or for remote server:"
echo "  ssh root@46.224.115.100 'cd /opt/marketing-tracker && docker-compose restart backend'"
echo
