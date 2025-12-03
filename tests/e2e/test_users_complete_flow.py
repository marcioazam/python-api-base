"""End-to-End tests for complete user lifecycle.

**Feature: application-layer-e2e-testing**
**Validates: Requirements Complete user flow through API**
"""

import pytest
from fastapi.testclient import TestClient
from typing import Generator

from main import app


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """Create test client for the application."""
    with TestClient(app) as test_client:
        yield test_client


class TestCompleteUserLifecycle:
    """End-to-end tests for complete user CRUD operations."""

    @pytest.mark.e2e
    def test_complete_user_lifecycle(self, client: TestClient) -> None:
        """Test complete user lifecycle: Create -> Get -> Update -> Delete.

        **Property: Complete CRUD Flow**
        **Validates: Requirements E2E.1**
        """
        # ========================================
        # STEP 1: CREATE USER
        # ========================================
        create_payload = {
            "email": "e2e.test@example.com",
            "password": "SecurePassword123!",
            "username": "e2euser",
            "display_name": "E2E Test User",
        }

        create_response = client.post("/api/v1/users", json=create_payload)

        # Validate creation
        assert create_response.status_code == 201, f"Create failed: {create_response.text}"
        created_user = create_response.json()
        assert created_user["email"] == "e2e.test@example.com"
        assert created_user["username"] == "e2euser"
        assert created_user["display_name"] == "E2E Test User"
        assert created_user["is_active"] is True
        assert "id" in created_user

        user_id = created_user["id"]

        # ========================================
        # STEP 2: GET USER BY ID
        # ========================================
        get_response = client.get(f"/api/v1/users/{user_id}")

        # Validate retrieval
        assert get_response.status_code == 200, f"Get failed: {get_response.text}"
        retrieved_user = get_response.json()
        assert retrieved_user["id"] == user_id
        assert retrieved_user["email"] == "e2e.test@example.com"
        assert retrieved_user["username"] == "e2euser"

        # ========================================
        # STEP 3: LIST USERS (should include created user)
        # ========================================
        list_response = client.get("/api/v1/users")

        # Validate list contains our user
        assert list_response.status_code == 200, f"List failed: {list_response.text}"
        users_list = list_response.json()
        assert "items" in users_list
        user_ids = [u["id"] for u in users_list["items"]]
        assert user_id in user_ids, "Created user not found in list"

        # ========================================
        # STEP 4: UPDATE USER
        # ========================================
        update_payload = {
            "username": "e2e_updated",
            "display_name": "Updated E2E User",
        }

        update_response = client.patch(f"/api/v1/users/{user_id}", json=update_payload)

        # Validate update
        assert update_response.status_code == 200, f"Update failed: {update_response.text}"
        updated_user = update_response.json()
        assert updated_user["id"] == user_id
        assert updated_user["username"] == "e2e_updated"
        assert updated_user["display_name"] == "Updated E2E User"
        # Email should remain unchanged
        assert updated_user["email"] == "e2e.test@example.com"

        # ========================================
        # STEP 5: VERIFY UPDATE PERSISTED
        # ========================================
        verify_response = client.get(f"/api/v1/users/{user_id}")

        assert verify_response.status_code == 200
        verified_user = verify_response.json()
        assert verified_user["username"] == "e2e_updated"
        assert verified_user["display_name"] == "Updated E2E User"

        # ========================================
        # STEP 6: DELETE USER
        # ========================================
        delete_response = client.delete(f"/api/v1/users/{user_id}")

        # Validate deletion
        assert delete_response.status_code == 204, f"Delete failed: {delete_response.text}"

        # ========================================
        # STEP 7: VERIFY USER IS DELETED
        # ========================================
        verify_deleted_response = client.get(f"/api/v1/users/{user_id}")

        # User should be deactivated (soft delete) - might return 404 or inactive user
        # Depending on implementation, adjust assertion:
        assert verify_deleted_response.status_code in [404, 200]
        if verify_deleted_response.status_code == 200:
            deleted_user = verify_deleted_response.json()
            # If soft delete, user should be inactive
            assert deleted_user.get("is_active") is False

    @pytest.mark.e2e
    def test_create_duplicate_email_rejected(self, client: TestClient) -> None:
        """Test that creating user with duplicate email is rejected.

        **Property: Duplicate Email Prevention E2E**
        **Validates: Requirements E2E.2**
        """
        # Create first user
        payload1 = {
            "email": "duplicate@example.com",
            "password": "Password123!",
        }

        response1 = client.post("/api/v1/users", json=payload1)
        assert response1.status_code == 201

        # Attempt to create second user with same email
        payload2 = {
            "email": "duplicate@example.com",  # Same email
            "password": "DifferentPassword123!",
            "username": "different_username",
        }

        response2 = client.post("/api/v1/users", json=payload2)

        # Should be rejected with 409 Conflict
        assert response2.status_code == 409
        error = response2.json()
        assert "Email already registered" in error["detail"]

    @pytest.mark.e2e
    def test_get_nonexistent_user_returns_404(self, client: TestClient) -> None:
        """Test that getting nonexistent user returns 404.

        **Property: Not Found Handling E2E**
        **Validates: Requirements E2E.3**
        """
        nonexistent_id = "nonexistent-user-12345"

        response = client.get(f"/api/v1/users/{nonexistent_id}")

        assert response.status_code == 404
        error = response.json()
        assert "not found" in error["detail"].lower()

    @pytest.mark.e2e
    def test_update_nonexistent_user_returns_404(self, client: TestClient) -> None:
        """Test that updating nonexistent user returns 404.

        **Property: Update Not Found E2E**
        **Validates: Requirements E2E.4**
        """
        nonexistent_id = "nonexistent-user-67890"
        update_payload = {"username": "newname"}

        response = client.patch(f"/api/v1/users/{nonexistent_id}", json=update_payload)

        assert response.status_code == 404
        error = response.json()
        assert "not found" in error["detail"].lower()

    @pytest.mark.e2e
    def test_delete_nonexistent_user_returns_404(self, client: TestClient) -> None:
        """Test that deleting nonexistent user returns 404.

        **Property: Delete Not Found E2E**
        **Validates: Requirements E2E.5**
        """
        nonexistent_id = "nonexistent-user-99999"

        response = client.delete(f"/api/v1/users/{nonexistent_id}")

        assert response.status_code == 404
        error = response.json()
        assert "not found" in error["detail"].lower()

    @pytest.mark.e2e
    def test_create_user_invalid_email_rejected(self, client: TestClient) -> None:
        """Test that invalid email format is rejected.

        **Property: Email Validation E2E**
        **Validates: Requirements E2E.6**
        """
        payload = {
            "email": "not-an-email",  # Invalid format
            "password": "Password123!",
        }

        response = client.post("/api/v1/users", json=payload)

        # Should be rejected with 422 Unprocessable Entity (validation error)
        assert response.status_code == 422

    @pytest.mark.e2e
    def test_create_user_weak_password_rejected(self, client: TestClient) -> None:
        """Test that weak password is rejected.

        **Property: Password Validation E2E**
        **Validates: Requirements E2E.7**
        """
        payload = {
            "email": "weakpwd@example.com",
            "password": "weak",  # Too short
        }

        response = client.post("/api/v1/users", json=payload)

        # Should be rejected with 422 (validation error from Pydantic or domain)
        assert response.status_code in [422, 400]

    @pytest.mark.e2e
    def test_list_users_pagination(self, client: TestClient) -> None:
        """Test list users with pagination parameters.

        **Property: Pagination E2E**
        **Validates: Requirements E2E.8**
        """
        # Create multiple users first
        for i in range(5):
            payload = {
                "email": f"pagination{i}@example.com",
                "password": "Password123!",
                "username": f"paginationuser{i}",
            }
            response = client.post("/api/v1/users", json=payload)
            assert response.status_code == 201

        # Test pagination: page 1, size 2
        response = client.get("/api/v1/users?page=1&page_size=2")

        assert response.status_code == 200
        result = response.json()
        assert "items" in result
        assert "total" in result
        assert "page" in result
        assert "size" in result
        assert result["page"] == 1
        assert result["size"] == 2
        # Should have exactly 2 items per page
        assert len(result["items"]) <= 2

    @pytest.mark.e2e
    def test_partial_update_preserves_other_fields(self, client: TestClient) -> None:
        """Test that partial update only modifies specified fields.

        **Property: Partial Update Preservation E2E**
        **Validates: Requirements E2E.9**
        """
        # Create user
        create_payload = {
            "email": "partial@example.com",
            "password": "Password123!",
            "username": "originalname",
            "display_name": "Original Display",
        }

        create_response = client.post("/api/v1/users", json=create_payload)
        assert create_response.status_code == 201
        user_id = create_response.json()["id"]

        # Update only username
        update_payload = {"username": "newname"}
        update_response = client.patch(f"/api/v1/users/{user_id}", json=update_payload)

        assert update_response.status_code == 200
        updated_user = update_response.json()

        # Username should be updated
        assert updated_user["username"] == "newname"
        # Display name should be preserved
        assert updated_user["display_name"] == "Original Display"
        # Email should be preserved
        assert updated_user["email"] == "partial@example.com"
