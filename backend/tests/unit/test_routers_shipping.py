"""
Unit tests for shipping router.
"""
import pytest
from datetime import date


@pytest.mark.unit
class TestShippingRouter:
    """Test shipping API endpoints."""

    def test_get_shipping_profiles_success(self, client, auth_headers):
        """Test getting shipping profiles successfully."""
        # First create a profile
        profile_data = {
            "name": "Test Profile",
            "description": "Test description",
            "priority": 10,
            "is_active": True,
            "match_conditions": {
                "field": "product_title",
                "operator": "contains",
                "value": "test"
            },
            "cost_rules": {
                "type": "fixed",
                "base_cost": 12.0
            }
        }

        client.post("/api/shipping/profiles", json=profile_data, headers=auth_headers)

        # Get all profiles
        response = client.get("/api/shipping/profiles", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_get_shipping_profiles_active_only(self, client, auth_headers):
        """Test getting only active profiles."""
        # Create active and inactive profiles
        active_profile = {
            "name": "Active Profile",
            "priority": 10,
            "is_active": True,
            "match_conditions": {"field": "product_title", "operator": "contains", "value": "test"},
            "cost_rules": {"type": "fixed", "base_cost": 10.0}
        }

        inactive_profile = {
            "name": "Inactive Profile",
            "priority": 20,
            "is_active": False,
            "match_conditions": {"field": "product_title", "operator": "contains", "value": "test"},
            "cost_rules": {"type": "fixed", "base_cost": 5.0}
        }

        client.post("/api/shipping/profiles", json=active_profile, headers=auth_headers)
        client.post("/api/shipping/profiles", json=inactive_profile, headers=auth_headers)

        # Get only active profiles
        response = client.get("/api/shipping/profiles?active_only=true", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        # All returned profiles should be active
        for profile in data:
            assert profile['is_active'] is True

    def test_get_shipping_profiles_database_error(self, client, auth_headers, monkeypatch):
        """Test getting profiles when database fails."""
        from app.database import ShippingDatabase

        def mock_get_profiles(*args, **kwargs):
            raise Exception("Database connection failed")

        monkeypatch.setattr(ShippingDatabase, "get_shipping_profiles", mock_get_profiles)

        response = client.get("/api/shipping/profiles", headers=auth_headers)

        assert response.status_code == 500
        assert "Failed to fetch shipping profiles" in response.json()['detail']

    def test_create_shipping_profile_success(self, client, auth_headers):
        """Test creating a shipping profile successfully."""
        profile_data = {
            "name": "New Profile",
            "description": "A new profile",
            "priority": 15,
            "is_active": True,
            "match_conditions": {
                "field": "product_title",
                "operator": "contains",
                "value": "widget"
            },
            "cost_rules": {
                "type": "fixed",
                "base_cost": 8.0
            }
        }

        response = client.post("/api/shipping/profiles", json=profile_data, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'profile_id' in data
        assert data['message'] == "Shipping profile created successfully"

    def test_create_shipping_profile_database_error(self, client, auth_headers, monkeypatch):
        """Test creating profile when database fails."""
        from app.database import ShippingDatabase

        def mock_upsert(*args, **kwargs):
            raise Exception("Database write failed")

        monkeypatch.setattr(ShippingDatabase, "upsert_shipping_profile", mock_upsert)

        profile_data = {
            "name": "Test Profile",
            "priority": 10,
            "match_conditions": {"field": "product_title", "operator": "contains", "value": "test"},
            "cost_rules": {"type": "fixed", "base_cost": 10.0}
        }

        response = client.post("/api/shipping/profiles", json=profile_data, headers=auth_headers)

        assert response.status_code == 500
        assert "Failed to create shipping profile" in response.json()['detail']

    def test_update_shipping_profile_success(self, client, auth_headers):
        """Test updating a shipping profile successfully."""
        # Create a profile first
        create_data = {
            "name": "Original Profile",
            "priority": 10,
            "is_active": True,
            "match_conditions": {"field": "product_title", "operator": "contains", "value": "test"},
            "cost_rules": {"type": "fixed", "base_cost": 10.0}
        }

        create_response = client.post("/api/shipping/profiles", json=create_data, headers=auth_headers)
        profile_id = create_response.json()['profile_id']

        # Update the profile
        update_data = {
            "name": "Updated Profile",
            "priority": 20
        }

        response = client.put(f"/api/shipping/profiles/{profile_id}", json=update_data, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['message'] == "Shipping profile updated successfully"

    def test_update_shipping_profile_with_none_values(self, client, auth_headers):
        """Test updating a shipping profile with None values (should be skipped)."""
        # Create a profile first
        create_data = {
            "name": "Original Profile",
            "description": "Original description",
            "priority": 10,
            "is_active": True,
            "match_conditions": {"field": "product_title", "operator": "contains", "value": "test"},
            "cost_rules": {"type": "fixed", "base_cost": 10.0}
        }

        create_response = client.post("/api/shipping/profiles", json=create_data, headers=auth_headers)
        profile_id = create_response.json()['profile_id']

        # Update with some None values (they should be ignored)
        update_data = {
            "name": "Updated Profile",
            "description": None,  # This should be skipped due to value is not None check
            "priority": 20
        }

        response = client.put(f"/api/shipping/profiles/{profile_id}", json=update_data, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

    def test_update_shipping_profile_not_found(self, client, auth_headers):
        """Test updating a non-existent profile."""
        update_data = {
            "name": "Updated Profile"
        }

        response = client.put("/api/shipping/profiles/nonexistent-id", json=update_data, headers=auth_headers)

        assert response.status_code == 404
        assert "Shipping profile not found" in response.json()['detail']

    def test_update_shipping_profile_database_error(self, client, auth_headers, monkeypatch):
        """Test updating profile when database fails."""
        from app.database import ShippingDatabase

        # Create a profile first
        create_data = {
            "name": "Test Profile",
            "priority": 10,
            "match_conditions": {"field": "product_title", "operator": "contains", "value": "test"},
            "cost_rules": {"type": "fixed", "base_cost": 10.0}
        }

        create_response = client.post("/api/shipping/profiles", json=create_data, headers=auth_headers)
        profile_id = create_response.json()['profile_id']

        # Now mock upsert to fail for the update
        def mock_upsert(*args, **kwargs):
            raise Exception("Database update failed")

        monkeypatch.setattr(ShippingDatabase, "upsert_shipping_profile", mock_upsert)

        update_data = {"name": "Updated"}
        response = client.put(f"/api/shipping/profiles/{profile_id}", json=update_data, headers=auth_headers)

        assert response.status_code == 500
        assert "Failed to update shipping profile" in response.json()['detail']

    def test_delete_shipping_profile_success(self, client, auth_headers):
        """Test deleting a shipping profile successfully."""
        # Create a profile first
        create_data = {
            "name": "Profile to Delete",
            "priority": 10,
            "match_conditions": {"field": "product_title", "operator": "contains", "value": "test"},
            "cost_rules": {"type": "fixed", "base_cost": 10.0}
        }

        create_response = client.post("/api/shipping/profiles", json=create_data, headers=auth_headers)
        profile_id = create_response.json()['profile_id']

        # Delete the profile
        response = client.delete(f"/api/shipping/profiles/{profile_id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['message'] == "Shipping profile deleted successfully"

    def test_delete_shipping_profile_database_error(self, client, auth_headers, monkeypatch):
        """Test deleting profile when database fails."""
        from app.database import ShippingDatabase

        def mock_delete(*args, **kwargs):
            raise Exception("Database delete failed")

        monkeypatch.setattr(ShippingDatabase, "delete_shipping_profile", mock_delete)

        response = client.delete("/api/shipping/profiles/some-id", headers=auth_headers)

        assert response.status_code == 500
        assert "Failed to delete shipping profile" in response.json()['detail']

    def test_test_profile_match_success(self, client, auth_headers):
        """Test profile matching test endpoint."""
        test_data = {
            "profile": {
                "name": "Test Profile",
                "priority": 10,
                "match_conditions": {
                    "field": "product_title",
                    "operator": "contains",
                    "value": "widget",
                    "case_sensitive": False
                },
                "cost_rules": {
                    "type": "fixed",
                    "base_cost": 12.0
                }
            },
            "test_data": {
                "product_title": "Super Widget",
                "order_subtotal": 100.0
            }
        }

        response = client.post("/api/shipping/profiles/test", json=test_data, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['matched'] is True
        assert data['calculated_cost'] == 12.0
        assert 'details' in data

    def test_test_profile_match_no_match(self, client, auth_headers):
        """Test profile matching when it doesn't match."""
        test_data = {
            "profile": {
                "name": "Test Profile",
                "priority": 10,
                "match_conditions": {
                    "field": "product_title",
                    "operator": "contains",
                    "value": "gadget"
                },
                "cost_rules": {
                    "type": "fixed",
                    "base_cost": 12.0
                }
            },
            "test_data": {
                "product_title": "Not a widget",
                "order_subtotal": 100.0
            }
        }

        response = client.post("/api/shipping/profiles/test", json=test_data, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['matched'] is False
        assert data['calculated_cost'] is None

    def test_test_profile_match_error(self, client, auth_headers, monkeypatch):
        """Test profile matching when an error occurs."""
        from app.routers import shipping

        def mock_evaluate_match(*args, **kwargs):
            raise Exception("Evaluation failed")

        monkeypatch.setattr(shipping, "evaluate_match_conditions", mock_evaluate_match)

        test_data = {
            "profile": {
                "name": "Test Profile",
                "priority": 10,
                "match_conditions": {"field": "product_title", "operator": "contains", "value": "test"},
                "cost_rules": {"type": "fixed", "base_cost": 10.0}
            },
            "test_data": {
                "product_title": "Test Product"
            }
        }

        response = client.post("/api/shipping/profiles/test", json=test_data, headers=auth_headers)

        assert response.status_code == 500
        assert "Failed to test profile" in response.json()['detail']
