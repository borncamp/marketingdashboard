"""
Simple SQLite database for user authentication.
"""
import sqlite3
import bcrypt
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path("/app/data/auth.db")  # Docker path
if not DB_PATH.parent.exists():
    DB_PATH = Path("data/auth.db")  # Local development path
    DB_PATH.parent.mkdir(exist_ok=True)


@contextmanager
def get_db():
    """Get database connection context manager."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Initialize the database with schema and default user."""
    with get_db() as conn:
        # Create users table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Check if default admin user exists
        cursor = conn.execute("SELECT COUNT(*) FROM users WHERE username = ?", ("admin",))
        if cursor.fetchone()[0] == 0:
            # Create default admin user with password "admin"
            default_password_hash = bcrypt.hashpw("admin".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                ("admin", default_password_hash)
            )


def verify_password(username: str, password: str) -> bool:
    """Verify username and password against database."""
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT password_hash FROM users WHERE username = ?",
            (username,)
        )
        row = cursor.fetchone()

        if not row:
            return False

        password_hash = row['password_hash']
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def change_password(username: str, new_password: str) -> bool:
    """Change user's password."""
    with get_db() as conn:
        new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor = conn.execute(
            "UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE username = ?",
            (new_hash, username)
        )
        return cursor.rowcount > 0


def user_exists(username: str) -> bool:
    """Check if user exists."""
    with get_db() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM users WHERE username = ?", (username,))
        return cursor.fetchone()[0] > 0


# Initialize database on module import
init_db()
