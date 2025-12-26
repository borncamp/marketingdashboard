#!/usr/bin/env python3
"""
Generate a bcrypt password hash for authentication.
Usage: python3 generate-password-hash.py
"""
import getpass
import bcrypt

def main():
    print("=== Password Hash Generator ===")
    print("This will generate a bcrypt hash for your password.")
    print()

    password = getpass.getpass("Enter password: ")
    password_confirm = getpass.getpass("Confirm password: ")

    if password != password_confirm:
        print("❌ Passwords don't match!")
        return

    if len(password) < 8:
        print("⚠️  Warning: Password is less than 8 characters. Consider using a stronger password.")

    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    print()
    print("✅ Password hash generated successfully!")
    print()
    print("Add this to your .env file:")
    print(f"AUTH_PASSWORD_HASH={hashed}")
    print()
    print("You can also set a custom username:")
    print("AUTH_USERNAME=your_username")
    print()

if __name__ == "__main__":
    main()
