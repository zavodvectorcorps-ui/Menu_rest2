"""
Test suite for Telegram Bot Expansion features (Iteration 13).
Tests: 
- POST /api/public/orders returns order with id
- GET /api/public/orders/{order_id}/status returns order status
- Status tracking flow (new -> in_progress -> completed)
- Telegram webhook callback_query handling (o_accept, o_done, o_cancel, c_done)
- Telegram commands (/orders, /calls, /stats)
- POST /api/public/staff-calls returns call with id
- WebSocket broadcast on order status change
- Backend regression tests
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL')

# Test credentials
SUPERADMIN_USERNAME = "admin"
SUPERADMIN_PASSWORD = "220066"
RESTAURANT_ID = "aa25189d-d668-4838-915a-c5d936547f3f"
REGULAR_TABLE_CODE = "697DCAA5"
PREORDER_TABLE_CODE = "6E32830E"


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


class TestPublicOrdersEndpoint:
    """Tests for POST /api/public/orders - order creation with ID"""

    def test_create_order_returns_id(self):
        """POST /api/public/orders should return order with id field"""
        response = requests.post(
            f"{BASE_URL}/api/public/orders",
            json={
                "table_code": REGULAR_TABLE_CODE,
                "items": [
                    {
                        "menu_item_id": "test-item-1",
                        "name": "TEST_Burger",
                        "quantity": 2,
                        "price": 15.50
                    }
                ],
                "notes": "Test order - check id returned"
            }
        )
        assert response.status_code == 200, f"Order creation failed: {response.text}"
        data = response.json()
        
        # Verify id is returned
        assert "id" in data, "Order should have id field"
        assert isinstance(data["id"], str), "Order id should be string"
        assert len(data["id"]) > 0, "Order id should not be empty"
        
        # Verify other fields
        assert data["status"] == "new"
        assert data["total"] == 31.0  # 2 * 15.50
        assert "restaurant_id" in data
        assert "created_at" in data
        
        return data["id"]

    def test_create_preorder_returns_id(self):
        """POST /api/public/orders for preorder should return order with id"""
        response = requests.post(
            f"{BASE_URL}/api/public/orders",
            json={
                "table_code": PREORDER_TABLE_CODE,
                "items": [
                    {
                        "menu_item_id": "test-item-pre",
                        "name": "TEST_PreorderDish",
                        "quantity": 1,
                        "price": 25.00
                    }
                ],
                "customer_name": "Test Customer",
                "customer_phone": "+375291234567",
                "preorder_date": "2026-01-20",
                "preorder_time": "18:00",
                "notes": ""
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify id and preorder fields
        assert "id" in data
        assert data["is_preorder"] == True
        assert data["customer_name"] == "Test Customer"


class TestOrderStatusEndpoint:
    """Tests for GET /api/public/orders/{order_id}/status endpoint"""

    def test_get_order_status_returns_status(self):
        """GET /api/public/orders/{order_id}/status should return order status"""
        # First create an order
        create_resp = requests.post(
            f"{BASE_URL}/api/public/orders",
            json={
                "table_code": REGULAR_TABLE_CODE,
                "items": [{"menu_item_id": "test", "name": "TEST_Item", "quantity": 1, "price": 10.0}],
                "notes": ""
            }
        )
        assert create_resp.status_code == 200
        order_id = create_resp.json()["id"]
        
        # Get status
        status_resp = requests.get(f"{BASE_URL}/api/public/orders/{order_id}/status")
        assert status_resp.status_code == 200
        data = status_resp.json()
        
        # Verify response structure
        assert "id" in data
        assert data["id"] == order_id
        assert "status" in data
        assert data["status"] == "new"
        assert "created_at" in data

    def test_get_order_status_invalid_id(self):
        """GET /api/public/orders/{invalid_id}/status should return 404"""
        response = requests.get(f"{BASE_URL}/api/public/orders/invalid-order-id-12345/status")
        assert response.status_code == 404

    def test_order_status_is_public(self):
        """GET /api/public/orders/{order_id}/status should not require auth"""
        # Create order
        create_resp = requests.post(
            f"{BASE_URL}/api/public/orders",
            json={
                "table_code": REGULAR_TABLE_CODE,
                "items": [{"menu_item_id": "test", "name": "TEST_Public", "quantity": 1, "price": 5.0}],
                "notes": ""
            }
        )
        order_id = create_resp.json()["id"]
        
        # Get status without auth - should work
        status_resp = requests.get(f"{BASE_URL}/api/public/orders/{order_id}/status")
        assert status_resp.status_code == 200


class TestOrderStatusFlow:
    """Tests for order status tracking flow: new -> in_progress -> completed"""

    def test_status_flow_via_admin_api(self, auth_headers):
        """Test order status can be updated via admin API and client sees changes"""
        # Create order
        create_resp = requests.post(
            f"{BASE_URL}/api/public/orders",
            json={
                "table_code": REGULAR_TABLE_CODE,
                "items": [{"menu_item_id": "flow-test", "name": "TEST_FlowItem", "quantity": 1, "price": 20.0}],
                "notes": "Flow test"
            }
        )
        assert create_resp.status_code == 200
        order_id = create_resp.json()["id"]
        
        # Initial status should be "new"
        status_resp = requests.get(f"{BASE_URL}/api/public/orders/{order_id}/status")
        assert status_resp.json()["status"] == "new"
        
        # Update to in_progress via admin API
        update_resp = requests.put(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/orders/{order_id}/status",
            json={"status": "in_progress"},
            headers=auth_headers
        )
        assert update_resp.status_code == 200
        
        # Client should see in_progress
        status_resp = requests.get(f"{BASE_URL}/api/public/orders/{order_id}/status")
        assert status_resp.json()["status"] == "in_progress"
        
        # Update to completed
        update_resp = requests.put(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/orders/{order_id}/status",
            json={"status": "completed"},
            headers=auth_headers
        )
        assert update_resp.status_code == 200
        
        # Client should see completed
        status_resp = requests.get(f"{BASE_URL}/api/public/orders/{order_id}/status")
        assert status_resp.json()["status"] == "completed"

    def test_status_cancelled(self, auth_headers):
        """Test order can be cancelled and client sees cancelled status"""
        # Create order
        create_resp = requests.post(
            f"{BASE_URL}/api/public/orders",
            json={
                "table_code": REGULAR_TABLE_CODE,
                "items": [{"menu_item_id": "cancel-test", "name": "TEST_CancelItem", "quantity": 1, "price": 15.0}],
                "notes": ""
            }
        )
        order_id = create_resp.json()["id"]
        
        # Cancel order
        update_resp = requests.put(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/orders/{order_id}/status",
            json={"status": "cancelled"},
            headers=auth_headers
        )
        assert update_resp.status_code == 200
        
        # Client should see cancelled
        status_resp = requests.get(f"{BASE_URL}/api/public/orders/{order_id}/status")
        assert status_resp.json()["status"] == "cancelled"


class TestTelegramWebhookCallbackQuery:
    """Tests for Telegram webhook handling callback_query (inline button presses)"""

    def test_callback_query_order_accept(self):
        """Webhook should handle o_accept callback_query"""
        # Create order first
        create_resp = requests.post(
            f"{BASE_URL}/api/public/orders",
            json={
                "table_code": REGULAR_TABLE_CODE,
                "items": [{"menu_item_id": "cb-test", "name": "TEST_CBItem", "quantity": 1, "price": 10.0}],
                "notes": ""
            }
        )
        order_id = create_resp.json()["id"]
        
        # Send callback_query to webhook
        response = requests.post(
            f"{BASE_URL}/api/telegram/webhook/{RESTAURANT_ID}",
            json={
                "callback_query": {
                    "id": "test_callback_123",
                    "data": f"o_accept_{order_id}",
                    "message": {
                        "chat": {"id": 123456789},
                        "message_id": 1,
                        "text": "Original order message"
                    }
                }
            }
        )
        assert response.status_code == 200
        assert response.json().get("ok") == True
        
        # Verify order status changed to in_progress
        status_resp = requests.get(f"{BASE_URL}/api/public/orders/{order_id}/status")
        assert status_resp.json()["status"] == "in_progress"

    def test_callback_query_order_done(self):
        """Webhook should handle o_done callback_query"""
        # Create and accept order
        create_resp = requests.post(
            f"{BASE_URL}/api/public/orders",
            json={
                "table_code": REGULAR_TABLE_CODE,
                "items": [{"menu_item_id": "done-test", "name": "TEST_DoneItem", "quantity": 1, "price": 10.0}],
                "notes": ""
            }
        )
        order_id = create_resp.json()["id"]
        
        # Send o_done callback
        response = requests.post(
            f"{BASE_URL}/api/telegram/webhook/{RESTAURANT_ID}",
            json={
                "callback_query": {
                    "id": "test_done_456",
                    "data": f"o_done_{order_id}",
                    "message": {
                        "chat": {"id": 123456789},
                        "message_id": 2,
                        "text": "Order message"
                    }
                }
            }
        )
        assert response.status_code == 200
        
        # Verify order status changed to completed
        status_resp = requests.get(f"{BASE_URL}/api/public/orders/{order_id}/status")
        assert status_resp.json()["status"] == "completed"

    def test_callback_query_order_cancel(self):
        """Webhook should handle o_cancel callback_query"""
        # Create order
        create_resp = requests.post(
            f"{BASE_URL}/api/public/orders",
            json={
                "table_code": REGULAR_TABLE_CODE,
                "items": [{"menu_item_id": "cancel-cb", "name": "TEST_CancelCB", "quantity": 1, "price": 10.0}],
                "notes": ""
            }
        )
        order_id = create_resp.json()["id"]
        
        # Send o_cancel callback
        response = requests.post(
            f"{BASE_URL}/api/telegram/webhook/{RESTAURANT_ID}",
            json={
                "callback_query": {
                    "id": "test_cancel_789",
                    "data": f"o_cancel_{order_id}",
                    "message": {
                        "chat": {"id": 123456789},
                        "message_id": 3,
                        "text": "Order message"
                    }
                }
            }
        )
        assert response.status_code == 200
        
        # Verify order status changed to cancelled
        status_resp = requests.get(f"{BASE_URL}/api/public/orders/{order_id}/status")
        assert status_resp.json()["status"] == "cancelled"

    def test_callback_query_call_done(self):
        """Webhook should handle c_done callback_query for staff calls"""
        # Create staff call
        create_resp = requests.post(
            f"{BASE_URL}/api/public/staff-calls",
            json={"table_code": REGULAR_TABLE_CODE}
        )
        assert create_resp.status_code == 200
        call_id = create_resp.json()["id"]
        
        # Send c_done callback
        response = requests.post(
            f"{BASE_URL}/api/telegram/webhook/{RESTAURANT_ID}",
            json={
                "callback_query": {
                    "id": "test_call_done",
                    "data": f"c_done_{call_id}",
                    "message": {
                        "chat": {"id": 123456789},
                        "message_id": 4,
                        "text": "Call message"
                    }
                }
            }
        )
        assert response.status_code == 200

    def test_callback_query_invalid_order(self):
        """Webhook should handle callback_query with invalid order ID gracefully"""
        response = requests.post(
            f"{BASE_URL}/api/telegram/webhook/{RESTAURANT_ID}",
            json={
                "callback_query": {
                    "id": "test_invalid",
                    "data": "o_accept_invalid-order-id-xyz",
                    "message": {
                        "chat": {"id": 123456789},
                        "message_id": 5,
                        "text": "Message"
                    }
                }
            }
        )
        assert response.status_code == 200  # Should still return OK, just handle gracefully


class TestTelegramCommands:
    """Tests for Telegram bot commands (/orders, /calls, /stats)"""

    def test_orders_command(self):
        """Webhook should handle /orders command"""
        response = requests.post(
            f"{BASE_URL}/api/telegram/webhook/{RESTAURANT_ID}",
            json={
                "message": {
                    "chat": {"id": 111222333, "username": "test_user", "first_name": "Test"},
                    "text": "/orders"
                }
            }
        )
        assert response.status_code == 200
        assert response.json().get("ok") == True

    def test_calls_command(self):
        """Webhook should handle /calls command"""
        response = requests.post(
            f"{BASE_URL}/api/telegram/webhook/{RESTAURANT_ID}",
            json={
                "message": {
                    "chat": {"id": 111222333, "username": "test_user", "first_name": "Test"},
                    "text": "/calls"
                }
            }
        )
        assert response.status_code == 200
        assert response.json().get("ok") == True

    def test_stats_command(self):
        """Webhook should handle /stats command"""
        response = requests.post(
            f"{BASE_URL}/api/telegram/webhook/{RESTAURANT_ID}",
            json={
                "message": {
                    "chat": {"id": 111222333, "username": "test_user", "first_name": "Test"},
                    "text": "/stats"
                }
            }
        )
        assert response.status_code == 200
        assert response.json().get("ok") == True

    def test_start_command_subscribes(self):
        """Webhook should handle /start command and subscribe user"""
        test_chat_id = str(uuid.uuid4())[:10]
        response = requests.post(
            f"{BASE_URL}/api/telegram/webhook/{RESTAURANT_ID}",
            json={
                "message": {
                    "chat": {"id": test_chat_id, "username": "new_user", "first_name": "New"},
                    "text": "/start"
                }
            }
        )
        assert response.status_code == 200
        assert response.json().get("ok") == True


class TestStaffCallsEndpoint:
    """Tests for POST /api/public/staff-calls - creates call with id"""

    def test_create_staff_call_returns_id(self):
        """POST /api/public/staff-calls should return call with id field"""
        response = requests.post(
            f"{BASE_URL}/api/public/staff-calls",
            json={"table_code": REGULAR_TABLE_CODE}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify id is returned
        assert "id" in data, "Staff call should have id field"
        assert isinstance(data["id"], str), "Call id should be string"
        assert len(data["id"]) > 0, "Call id should not be empty"
        
        # Verify other fields
        assert data["status"] == "pending"
        assert "restaurant_id" in data
        assert "table_id" in data
        assert "table_number" in data
        assert "created_at" in data

    def test_create_staff_call_with_call_type_returns_id(self, auth_headers):
        """POST /api/public/staff-calls with call_type should return call with id"""
        # Get call types
        ct_resp = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/call-types",
            headers=auth_headers
        )
        call_types = ct_resp.json()
        
        if call_types:
            response = requests.post(
                f"{BASE_URL}/api/public/staff-calls",
                json={"table_code": REGULAR_TABLE_CODE, "call_type_id": call_types[0]["id"]}
            )
            assert response.status_code == 200
            data = response.json()
            
            assert "id" in data
            assert data["call_type_id"] == call_types[0]["id"]
            assert data["call_type_name"] == call_types[0]["name"]


class TestBackendRegression:
    """Regression tests for existing functionality"""

    def test_login_works(self):
        """POST /api/auth/login should work"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": SUPERADMIN_USERNAME, "password": SUPERADMIN_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "restaurants" in data

    def test_restaurants_endpoint(self, auth_headers):
        """GET /api/restaurants should work"""
        response = requests.get(f"{BASE_URL}/api/restaurants", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_categories_endpoint(self, auth_headers):
        """GET /api/restaurants/{id}/categories should work"""
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/categories",
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_menu_items_endpoint(self, auth_headers):
        """GET /api/restaurants/{id}/menu-items should work"""
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/menu-items",
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_labels_endpoint(self, auth_headers):
        """GET /api/restaurants/{id}/labels should work"""
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/labels",
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_tables_endpoint(self, auth_headers):
        """GET /api/restaurants/{id}/tables should work"""
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/tables",
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_settings_endpoint(self, auth_headers):
        """GET /api/restaurants/{id}/settings should work"""
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/settings",
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_analytics_endpoint(self, auth_headers):
        """GET /api/restaurants/{id}/analytics should work"""
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/analytics",
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_orders_endpoint(self, auth_headers):
        """GET /api/restaurants/{id}/orders should work"""
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/orders",
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_staff_calls_admin_endpoint(self, auth_headers):
        """GET /api/restaurants/{id}/staff-calls should work"""
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/staff-calls",
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_public_menu_endpoint(self):
        """GET /api/public/menu/{table_code} should work"""
        response = requests.get(f"{BASE_URL}/api/public/menu/{REGULAR_TABLE_CODE}")
        assert response.status_code == 200
        data = response.json()
        assert "restaurant" in data
        assert "items" in data
        assert "categories" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
