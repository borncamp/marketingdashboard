"""
Shared fixtures for all tests.
"""
import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_database, get_db_connection, DATABASE_PATH
from app import db as auth_db


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def test_db():
    """Create isolated test database for each test."""
    # Create temp database
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    auth_db_fd, auth_db_path = tempfile.mkstemp(suffix='.db')

    # Store original paths
    original_db_path = DATABASE_PATH
    original_auth_db_path = auth_db.DB_PATH

    # Override database paths
    import app.database
    import app.db
    app.database.DATABASE_PATH = Path(db_path)
    app.db.DB_PATH = Path(auth_db_path)

    # Initialize schemas
    init_database()
    auth_db.init_db()

    yield db_path

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)
    os.close(auth_db_fd)
    os.unlink(auth_db_path)

    # Restore original paths
    app.database.DATABASE_PATH = original_db_path
    app.db.DB_PATH = original_auth_db_path


@pytest.fixture
def client(test_db):
    """FastAPI test client with isolated database."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers():
    """Valid auth headers for testing."""
    import base64
    # Default admin credentials
    credentials = base64.b64encode(b"admin:admin").decode()
    return {"Authorization": f"Basic {credentials}"}


@pytest.fixture
def create_test_user(test_db):
    """Factory fixture to create test users."""
    import bcrypt
    from app import db as auth_db

    def _create_user(username="testuser", password="testpass"):
        # Manually create user in auth database
        with auth_db.get_db() as conn:
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, password_hash)
            )

        import base64
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        return {"Authorization": f"Basic {credentials}"}

    return _create_user


@pytest.fixture
def sample_campaign():
    """Sample campaign data for testing."""
    return {
        "id": "test-campaign-123",
        "name": "Test Campaign",
        "status": "ENABLED",
        "platform": "google_ads"
    }


@pytest.fixture
def sample_order():
    """Sample Shopify order data for testing."""
    from datetime import date
    return {
        "id": "12345",
        "order_number": 1001,
        "order_date": str(date.today()),  # Use today's date so it appears in recent queries
        "customer_email": "test@example.com",
        "subtotal": 100.00,
        "total_price": 112.00,
        "shipping_charged": 12.00,
        "currency": "USD",
        "financial_status": "paid",
        "fulfillment_status": "fulfilled"
    }


@pytest.fixture
def sample_order_items():
    """Sample order line items for testing."""
    return [
        {
            "product_id": "999",
            "variant_id": "888",
            "product_title": "Test Product",
            "variant_title": "Small",
            "quantity": 1,
            "price": 100.00,
            "total": 100.00
        }
    ]


@pytest.fixture
def sample_shipping_profile():
    """Sample shipping profile for testing."""
    return {
        "id": "profile-123",
        "name": "Test Shipping Rule",
        "description": "Test rule for testing",
        "priority": 10,
        "is_active": True,
        "is_default": False,
        "match_conditions": {
            "field": "product_title",
            "operator": "contains",
            "value": "test",
            "case_sensitive": False
        },
        "cost_rules": {
            "type": "fixed",
            "base_cost": 10.0
        }
    }
