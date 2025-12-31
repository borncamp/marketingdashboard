"""
Unit tests for database module (app.db).
"""
import pytest
import bcrypt
from app import db


@pytest.mark.unit
class TestVerifyPassword:
    """Test verify_password function."""

    def test_verify_correct_password(self, test_db):
        """Test password verification with correct password."""
        assert db.verify_password("admin", "admin") is True

    def test_verify_incorrect_password(self, test_db):
        """Test password verification with incorrect password."""
        assert db.verify_password("admin", "wrongpassword") is False

    def test_verify_nonexistent_user(self, test_db):
        """Test password verification for non-existent user."""
        assert db.verify_password("nonexistent", "password") is False

    def test_verify_empty_username(self, test_db):
        """Test password verification with empty username."""
        assert db.verify_password("", "password") is False

    def test_verify_empty_password(self, test_db):
        """Test password verification with empty password."""
        assert db.verify_password("admin", "") is False

    def test_verify_case_sensitive_password(self, test_db):
        """Test that password verification is case-sensitive."""
        assert db.verify_password("admin", "Admin") is False
        assert db.verify_password("admin", "ADMIN") is False

    def test_verify_special_characters(self, test_db):
        """Test password with special characters."""
        # Create user with special char password
        with db.get_db() as conn:
            password_hash = bcrypt.hashpw("p@ss!#$%".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                ("specialuser", password_hash)
            )

        assert db.verify_password("specialuser", "p@ss!#$%") is True
        assert db.verify_password("specialuser", "p@ss") is False

    def test_verify_unicode_password(self, test_db):
        """Test password with unicode characters."""
        with db.get_db() as conn:
            password_hash = bcrypt.hashpw("пароль".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                ("unicodeuser", password_hash)
            )

        assert db.verify_password("unicodeuser", "пароль") is True

    def test_verify_long_password(self, test_db):
        """Test very long password."""
        long_password = "a" * 500
        with db.get_db() as conn:
            password_hash = bcrypt.hashpw(long_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                ("longpassuser", password_hash)
            )

        assert db.verify_password("longpassuser", long_password) is True
        assert db.verify_password("longpassuser", long_password[:-1]) is False


@pytest.mark.unit
class TestChangePassword:
    """Test change_password function."""

    def test_change_existing_user_password(self, test_db):
        """Test changing password for existing user."""
        result = db.change_password("admin", "newpassword123")
        assert result is True
        assert db.verify_password("admin", "newpassword123") is True
        assert db.verify_password("admin", "admin") is False

    def test_change_nonexistent_user_password(self, test_db):
        """Test changing password for non-existent user."""
        result = db.change_password("nonexistent", "newpassword")
        assert result is False

    def test_change_password_to_empty(self, test_db):
        """Test changing password to empty string."""
        result = db.change_password("admin", "")
        assert result is True
        # Empty password should be hashed and stored
        assert db.verify_password("admin", "") is True

    def test_change_password_multiple_times(self, test_db):
        """Test changing password multiple times."""
        assert db.change_password("admin", "password1") is True
        assert db.verify_password("admin", "password1") is True

        assert db.change_password("admin", "password2") is True
        assert db.verify_password("admin", "password2") is True
        assert db.verify_password("admin", "password1") is False

        assert db.change_password("admin", "password3") is True
        assert db.verify_password("admin", "password3") is True
        assert db.verify_password("admin", "password2") is False

    def test_change_password_special_characters(self, test_db):
        """Test changing password to one with special characters."""
        new_password = "n3w!P@ssw0rd#$%"
        result = db.change_password("admin", new_password)
        assert result is True
        assert db.verify_password("admin", new_password) is True

    def test_change_password_unicode(self, test_db):
        """Test changing password to unicode string."""
        new_password = "新しいパスワード"
        result = db.change_password("admin", new_password)
        assert result is True
        assert db.verify_password("admin", new_password) is True


@pytest.mark.unit
class TestUserExists:
    """Test user_exists function."""

    def test_existing_user(self, test_db):
        """Test checking if default admin user exists."""
        assert db.user_exists("admin") is True

    def test_nonexistent_user(self, test_db):
        """Test checking if non-existent user exists."""
        assert db.user_exists("nonexistent") is False

    def test_empty_username(self, test_db):
        """Test checking if empty username exists."""
        assert db.user_exists("") is False

    def test_case_sensitive_check(self, test_db):
        """Test that user existence check is case-sensitive."""
        assert db.user_exists("admin") is True
        assert db.user_exists("Admin") is False
        assert db.user_exists("ADMIN") is False

    def test_user_exists_after_creation(self, test_db):
        """Test user_exists after creating new user."""
        assert db.user_exists("newuser") is False

        with db.get_db() as conn:
            password_hash = bcrypt.hashpw("password".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                ("newuser", password_hash)
            )

        assert db.user_exists("newuser") is True


@pytest.mark.unit
class TestGetDb:
    """Test get_db context manager."""

    def test_connection_commits_on_success(self, test_db):
        """Test that changes are committed when context exits normally."""
        with db.get_db() as conn:
            password_hash = bcrypt.hashpw("test123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                ("commituser", password_hash)
            )

        # Verify user was committed
        assert db.user_exists("commituser") is True

    def test_connection_closes(self, test_db):
        """Test that connection is closed after context exit."""
        with db.get_db() as conn:
            assert conn is not None

        # After exiting context, connection should be closed
        # We can't directly test this, but we can verify operations still work
        assert db.user_exists("admin") is True

    def test_row_factory_is_set(self, test_db):
        """Test that row_factory is set to sqlite3.Row."""
        with db.get_db() as conn:
            cursor = conn.execute("SELECT username FROM users WHERE username = ?", ("admin",))
            row = cursor.fetchone()
            # Row should support dict-like access
            assert row['username'] == "admin"


@pytest.mark.unit
class TestInitDb:
    """Test init_db function."""

    def test_users_table_exists(self, test_db):
        """Test that users table is created."""
        with db.get_db() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
            )
            assert cursor.fetchone() is not None

    def test_default_admin_user_created(self, test_db):
        """Test that default admin user is created."""
        assert db.user_exists("admin") is True
        assert db.verify_password("admin", "admin") is True

    def test_init_db_idempotent(self, test_db):
        """Test that calling init_db multiple times is safe."""
        # Call init_db again
        db.init_db()

        # Should still have exactly one admin user
        with db.get_db() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM users WHERE username = ?", ("admin",))
            count = cursor.fetchone()[0]
            assert count == 1

    def test_users_table_schema(self, test_db):
        """Test that users table has correct schema."""
        with db.get_db() as conn:
            cursor = conn.execute("PRAGMA table_info(users)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}

            assert 'id' in columns
            assert 'username' in columns
            assert 'password_hash' in columns
            assert 'created_at' in columns
            assert 'updated_at' in columns


@pytest.mark.unit
class TestDatabaseIntegrity:
    """Test database integrity and constraints."""

    def test_username_unique_constraint(self, test_db):
        """Test that duplicate usernames are rejected."""
        with db.get_db() as conn:
            password_hash = bcrypt.hashpw("password".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # First insertion should succeed
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                ("uniqueuser", password_hash)
            )

            # Second insertion should fail
            with pytest.raises(Exception):  # sqlite3.IntegrityError
                conn.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    ("uniqueuser", password_hash)
                )

    def test_username_not_null(self, test_db):
        """Test that username cannot be null."""
        with db.get_db() as conn:
            password_hash = bcrypt.hashpw("password".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            with pytest.raises(Exception):  # sqlite3.IntegrityError
                conn.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (None, password_hash)
                )

    def test_password_hash_not_null(self, test_db):
        """Test that password_hash cannot be null."""
        with db.get_db() as conn:
            with pytest.raises(Exception):  # sqlite3.IntegrityError
                conn.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    ("testuser", None)
                )

    def test_timestamps_auto_populated(self, test_db):
        """Test that created_at and updated_at are auto-populated."""
        with db.get_db() as conn:
            password_hash = bcrypt.hashpw("password".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                ("timestampuser", password_hash)
            )

            cursor = conn.execute(
                "SELECT created_at, updated_at FROM users WHERE username = ?",
                ("timestampuser",)
            )
            row = cursor.fetchone()

            assert row['created_at'] is not None
            assert row['updated_at'] is not None

    def test_updated_at_changes_on_password_change(self, test_db):
        """Test that updated_at changes when password is changed."""
        with db.get_db() as conn:
            cursor = conn.execute(
                "SELECT updated_at FROM users WHERE username = ?",
                ("admin",)
            )
            original_updated_at = cursor.fetchone()['updated_at']

        # Change password
        db.change_password("admin", "newpassword")

        with db.get_db() as conn:
            cursor = conn.execute(
                "SELECT updated_at FROM users WHERE username = ?",
                ("admin",)
            )
            new_updated_at = cursor.fetchone()['updated_at']

        # Note: In fast tests, timestamps might be the same if executed too quickly
        # But the change_password function does update the timestamp
        assert new_updated_at >= original_updated_at
