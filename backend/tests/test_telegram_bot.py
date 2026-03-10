"""
Test suite for Telegram Bot management features.
Tests: GET/PUT/DELETE telegram-bot endpoints, webhook handling, staff call/order notifications
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL')

# Test credentials
SUPERADMIN_USERNAME = "admin"
SUPERADMIN_PASSWORD = "220066"
RESTAURANT_ID = "aa25189d-d668-4838-915a-c5d936547f3f"  # Мята Спортивная


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for superadmin"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": SUPERADMIN_USERNAME, "password": SUPERADMIN_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    """Headers with Bearer token"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def table_code(auth_headers):
    """Get a table code for testing public endpoints"""
    response = requests.get(
        f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/tables",
        headers=auth_headers
    )
    assert response.status_code == 200
    tables = response.json()
    if tables:
        return tables[0]["code"]
    # If no tables, create one
    response = requests.post(
        f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/tables",
        json={"number": 999, "name": "Test Table"},
        headers=auth_headers
    )
    assert response.status_code == 200
    return response.json()["code"]


class TestTelegramBotEndpoints:
    """Tests for Telegram bot management endpoints"""

    def test_get_telegram_bot_requires_auth(self):
        """GET /api/restaurants/{id}/telegram-bot should require authentication"""
        response = requests.get(f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/telegram-bot")
        assert response.status_code == 401

    def test_get_telegram_bot_with_auth(self, auth_headers):
        """GET /api/restaurants/{id}/telegram-bot should return bot info with auth"""
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/telegram-bot",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should have required fields
        assert "bot_token" in data
        assert "bot_info" in data
        assert "webhook_set" in data
        assert "subscribers" in data
        
        # bot_token should be string (empty or not)
        assert isinstance(data["bot_token"], str)
        # subscribers should be list
        assert isinstance(data["subscribers"], list)

    def test_put_telegram_bot_invalid_token(self, auth_headers):
        """PUT /api/restaurants/{id}/telegram-bot with invalid token should return 400"""
        response = requests.put(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/telegram-bot",
            json={"telegram_bot_token": "invalid_token_12345"},
            headers=auth_headers
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        # Should mention invalid token
        assert "невалидный" in data["detail"].lower() or "invalid" in data["detail"].lower() or "token" in data["detail"].lower()

    def test_put_telegram_bot_empty_token(self, auth_headers):
        """PUT /api/restaurants/{id}/telegram-bot with empty token should be accepted (clears bot)"""
        response = requests.put(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/telegram-bot",
            json={"telegram_bot_token": ""},
            headers=auth_headers
        )
        # Empty token should work (to clear the bot)
        assert response.status_code == 200

    def test_delete_telegram_bot(self, auth_headers):
        """DELETE /api/restaurants/{id}/telegram-bot should disconnect bot"""
        response = requests.delete(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/telegram-bot",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        
        # Verify bot is disconnected
        get_response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/telegram-bot",
            headers=auth_headers
        )
        assert get_response.status_code == 200
        assert get_response.json()["bot_token"] == ""

    def test_delete_telegram_bot_requires_auth(self):
        """DELETE /api/restaurants/{id}/telegram-bot should require auth"""
        response = requests.delete(f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/telegram-bot")
        assert response.status_code == 401


class TestTelegramWebhook:
    """Tests for Telegram webhook endpoint (public)"""

    def test_webhook_endpoint_is_public(self):
        """POST /api/telegram/webhook/{restaurant_id} should be public (no auth required)"""
        response = requests.post(
            f"{BASE_URL}/api/telegram/webhook/{RESTAURANT_ID}",
            json={}  # Empty update
        )
        # Should not return 401 - endpoint is public
        assert response.status_code != 401
        # Empty message should be OK
        assert response.status_code == 200

    def test_webhook_handles_start_command(self):
        """POST /api/telegram/webhook/{restaurant_id} should handle /start command"""
        test_chat_id = str(uuid.uuid4())[:10]
        response = requests.post(
            f"{BASE_URL}/api/telegram/webhook/{RESTAURANT_ID}",
            json={
                "message": {
                    "chat": {
                        "id": test_chat_id,
                        "username": "test_user",
                        "first_name": "Test"
                    },
                    "text": "/start"
                }
            }
        )
        # Should return OK even if bot not configured (graceful handling)
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True

    def test_webhook_handles_empty_message(self):
        """POST /api/telegram/webhook/{restaurant_id} should handle empty message"""
        response = requests.post(
            f"{BASE_URL}/api/telegram/webhook/{RESTAURANT_ID}",
            json={"message": {}}
        )
        assert response.status_code == 200
        assert response.json().get("ok") == True


class TestNotificationsWithoutBot:
    """Tests that staff calls and orders work without Telegram bot configured"""

    def test_staff_call_without_bot(self, auth_headers, table_code):
        """POST /api/public/staff-calls should work without bot configured"""
        # First ensure bot is disconnected
        requests.delete(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/telegram-bot",
            headers=auth_headers
        )
        
        # Now create a staff call
        response = requests.post(
            f"{BASE_URL}/api/public/staff-calls",
            json={"table_code": table_code}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should create staff call successfully
        assert "id" in data
        assert "restaurant_id" in data
        assert data["table_id"] is not None
        assert "status" in data
        assert data["status"] == "pending"

    def test_staff_call_with_call_type(self, auth_headers, table_code):
        """POST /api/public/staff-calls with call_type_id should work"""
        # Get call types
        ct_response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/call-types",
            headers=auth_headers
        )
        assert ct_response.status_code == 200
        call_types = ct_response.json()
        
        if call_types:
            call_type_id = call_types[0]["id"]
            response = requests.post(
                f"{BASE_URL}/api/public/staff-calls",
                json={"table_code": table_code, "call_type_id": call_type_id}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["call_type_id"] == call_type_id
            assert data["call_type_name"] == call_types[0]["name"]

    def test_order_without_bot(self, auth_headers, table_code):
        """POST /api/public/orders should work without bot configured"""
        # Ensure bot is disconnected
        requests.delete(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/telegram-bot",
            headers=auth_headers
        )
        
        # Create an order
        response = requests.post(
            f"{BASE_URL}/api/public/orders",
            json={
                "table_code": table_code,
                "items": [
                    {
                        "menu_item_id": "test-item-1",
                        "name": "Test Item",
                        "quantity": 2,
                        "price": 10.50
                    }
                ],
                "notes": "Test order without bot"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should create order successfully
        assert "id" in data
        assert "restaurant_id" in data
        assert "table_id" in data
        assert data["total"] == 21.0  # 2 * 10.50
        assert data["status"] == "new"
        assert len(data["items"]) == 1

    def test_staff_call_invalid_table(self):
        """POST /api/public/staff-calls with invalid table should return 404"""
        response = requests.post(
            f"{BASE_URL}/api/public/staff-calls",
            json={"table_code": "INVALID123"}
        )
        assert response.status_code == 404

    def test_order_invalid_table(self):
        """POST /api/public/orders with invalid table should return 404"""
        response = requests.post(
            f"{BASE_URL}/api/public/orders",
            json={
                "table_code": "INVALID123",
                "items": [{"menu_item_id": "x", "name": "X", "quantity": 1, "price": 1}]
            }
        )
        assert response.status_code == 404


class TestPublicEndpointsExist:
    """Verify public endpoints use correct URL pattern"""

    def test_public_staff_calls_endpoint_exists(self, table_code):
        """POST /api/public/staff-calls should exist"""
        response = requests.post(
            f"{BASE_URL}/api/public/staff-calls",
            json={"table_code": table_code}
        )
        # 404 would be method not found, 422 would be validation error
        assert response.status_code in [200, 422, 404]
        # If 404, it should be "table not found", not "endpoint not found"
        if response.status_code == 404:
            assert "стол" in response.json().get("detail", "").lower() or "table" in response.json().get("detail", "").lower()

    def test_public_orders_endpoint_exists(self, table_code):
        """POST /api/public/orders should exist"""
        response = requests.post(
            f"{BASE_URL}/api/public/orders",
            json={
                "table_code": table_code,
                "items": [{"menu_item_id": "test", "name": "Test", "quantity": 1, "price": 1.0}]
            }
        )
        assert response.status_code in [200, 422, 404]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
