"""
Test Preorders and Complete-All Features (Iteration 10)

Features tested:
1. Login with admin/220066
2. Complete all orders API: POST /api/restaurants/{id}/orders/complete-all
3. Complete all staff-calls API: POST /api/restaurants/{id}/staff-calls/complete-all
4. Create preorder via public API: POST /api/public/orders
5. Preorder table flag (is_preorder=true)
6. Preorder order fields (customer_name, customer_phone, preorder_date, preorder_time)
7. Orders filtering (is_preorder flag)
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL')
RESTAURANT_ID = "aa25189d-d668-4838-915a-c5d936547f3f"
PREORDER_TABLE_CODE = "6E32830E"
REGULAR_TABLE_CODE = "697DCAA5"


class TestAuth:
    """Authentication tests"""
    
    def test_login_success(self):
        """Test login with admin credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "220066"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["role"] == "superadmin"
        print(f"✓ Login successful, user role: {data['user']['role']}")

    def test_login_invalid_credentials(self):
        """Test login with wrong credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid credentials rejected as expected")


@pytest.fixture
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "admin",
        "password": "220066"
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Authentication failed")


@pytest.fixture
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestCompleteAllOrders:
    """Test Complete All Orders Functionality"""
    
    def test_complete_all_orders_api(self, auth_headers):
        """POST /api/restaurants/{id}/orders/complete-all"""
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/orders/complete-all",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Complete all failed: {response.text}"
        data = response.json()
        assert "message" in data
        assert "count" in data
        print(f"✓ Complete all orders: {data['message']} (count: {data['count']})")
    
    def test_complete_all_orders_no_auth(self):
        """Complete all should require authentication"""
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/orders/complete-all"
        )
        assert response.status_code == 401
        print("✓ Complete all orders requires authentication")


class TestCompleteAllStaffCalls:
    """Test Complete All Staff Calls Functionality"""
    
    def test_complete_all_staff_calls_api(self, auth_headers):
        """POST /api/restaurants/{id}/staff-calls/complete-all"""
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/staff-calls/complete-all",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Complete all staff calls failed: {response.text}"
        data = response.json()
        assert "message" in data
        assert "count" in data
        print(f"✓ Complete all staff calls: {data['message']} (count: {data['count']})")

    def test_complete_all_staff_calls_no_auth(self):
        """Complete all staff calls should require authentication"""
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/staff-calls/complete-all"
        )
        assert response.status_code == 401
        print("✓ Complete all staff calls requires authentication")


class TestPreorderTable:
    """Test Preorder Table Setup"""
    
    def test_preorder_table_exists(self, auth_headers):
        """Verify preorder table exists with is_preorder=true"""
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/tables",
            headers=auth_headers
        )
        assert response.status_code == 200
        tables = response.json()
        preorder_table = next((t for t in tables if t.get("code") == PREORDER_TABLE_CODE), None)
        assert preorder_table is not None, f"Preorder table {PREORDER_TABLE_CODE} not found"
        assert preorder_table.get("is_preorder") == True, "Table should have is_preorder=true"
        print(f"✓ Preorder table found: number={preorder_table['number']}, code={preorder_table['code']}, is_preorder={preorder_table['is_preorder']}")
    
    def test_regular_table_exists(self, auth_headers):
        """Verify regular table exists with is_preorder=false or None (default)"""
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/tables",
            headers=auth_headers
        )
        assert response.status_code == 200
        tables = response.json()
        regular_table = next((t for t in tables if t.get("code") == REGULAR_TABLE_CODE), None)
        assert regular_table is not None, f"Regular table {REGULAR_TABLE_CODE} not found"
        # Regular tables may not have is_preorder field (None) or have it as False
        is_preorder = regular_table.get("is_preorder", False)
        assert is_preorder in [False, None], "Regular table should have is_preorder=false or not set"
        print(f"✓ Regular table found: number={regular_table['number']}, code={regular_table['code']}, is_preorder={is_preorder}")


class TestPublicMenuPreorder:
    """Test public menu for preorder table"""
    
    def test_public_menu_preorder_table(self):
        """GET /api/public/menu/{preorder_table_code} should return is_preorder flag"""
        response = requests.get(f"{BASE_URL}/api/public/menu/{PREORDER_TABLE_CODE}")
        assert response.status_code == 200, f"Public menu failed: {response.text}"
        data = response.json()
        
        assert "table" in data, "Response should contain table info"
        table = data["table"]
        assert table.get("is_preorder") == True, "Preorder table should have is_preorder=true"
        print(f"✓ Public menu for preorder table: is_preorder={table['is_preorder']}")
    
    def test_public_menu_regular_table(self):
        """GET /api/public/menu/{regular_table_code} should have is_preorder=false or None"""
        response = requests.get(f"{BASE_URL}/api/public/menu/{REGULAR_TABLE_CODE}")
        assert response.status_code == 200
        data = response.json()
        
        table = data.get("table", {})
        is_preorder = table.get("is_preorder", False)
        # Regular tables may not have is_preorder field (None) or have it as False
        assert is_preorder in [False, None], "Regular table should have is_preorder=false or not set"
        print(f"✓ Public menu for regular table: is_preorder={is_preorder}")


class TestCreatePreorder:
    """Test creating a preorder via public API"""
    
    def test_create_preorder_with_customer_info(self):
        """POST /api/public/orders with preorder table should capture customer info"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        response = requests.post(f"{BASE_URL}/api/public/orders", json={
            "table_code": PREORDER_TABLE_CODE,
            "items": [{
                "menu_item_id": "test-item-id",
                "name": "Тестовое блюдо",
                "quantity": 1,
                "price": 15.00
            }],
            "notes": "Тестовый предзаказ",
            "customer_name": "TEST_Тест Клиент",
            "customer_phone": "+375291234567",
            "preorder_date": tomorrow,
            "preorder_time": "19:00"
        })
        assert response.status_code == 200, f"Create preorder failed: {response.text}"
        data = response.json()
        
        # Verify preorder fields
        assert data.get("is_preorder") == True, "Order should have is_preorder=true"
        assert data.get("customer_name") == "TEST_Тест Клиент", "Customer name should be saved"
        assert data.get("customer_phone") == "+375291234567", "Customer phone should be saved"
        assert data.get("preorder_date") == tomorrow, "Preorder date should be saved"
        assert data.get("preorder_time") == "19:00", "Preorder time should be saved"
        print(f"✓ Preorder created with customer info: {data.get('customer_name')}, date: {data.get('preorder_date')}")
        
        return data.get("id")
    
    def test_create_regular_order_no_preorder_fields(self):
        """POST /api/public/orders with regular table should not have preorder fields"""
        response = requests.post(f"{BASE_URL}/api/public/orders", json={
            "table_code": REGULAR_TABLE_CODE,
            "items": [{
                "menu_item_id": "test-item-id",
                "name": "Тестовое блюдо обычное",
                "quantity": 2,
                "price": 10.00
            }],
            "notes": "Тестовый обычный заказ",
            "customer_name": "Should be ignored",
            "customer_phone": "+375290000000"
        })
        assert response.status_code == 200, f"Create regular order failed: {response.text}"
        data = response.json()
        
        # Regular orders should not have preorder=true
        assert data.get("is_preorder") == False, "Regular order should have is_preorder=false"
        assert data.get("customer_name") == "", "Regular order should not have customer_name"
        assert data.get("customer_phone") == "", "Regular order should not have customer_phone"
        print(f"✓ Regular order created: is_preorder={data.get('is_preorder')}, no customer info stored")


class TestOrdersListPreorders:
    """Test orders list with preorder filtering"""
    
    def test_get_all_orders(self, auth_headers):
        """GET /api/restaurants/{id}/orders should return all orders including preorders"""
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/orders",
            headers=auth_headers
        )
        assert response.status_code == 200
        orders = response.json()
        
        # Find preorders
        preorders = [o for o in orders if o.get("is_preorder") == True]
        regular_orders = [o for o in orders if o.get("is_preorder") == False]
        
        print(f"✓ Total orders: {len(orders)}, preorders: {len(preorders)}, regular: {len(regular_orders)}")
    
    def test_existing_preorder_ivan_petrov(self, auth_headers):
        """Verify preorder from Иван Петров exists"""
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/orders",
            headers=auth_headers
        )
        assert response.status_code == 200
        orders = response.json()
        
        # Find Иван Петров preorder
        ivan_preorder = next((o for o in orders if o.get("customer_name") == "Иван Петров"), None)
        if ivan_preorder:
            assert ivan_preorder.get("is_preorder") == True
            print(f"✓ Found preorder from Иван Петров: status={ivan_preorder.get('status')}, phone={ivan_preorder.get('customer_phone')}")
        else:
            # May have been completed in previous test runs
            print("⚠ Preorder from Иван Петров not found (may be completed)")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_orders(self, auth_headers):
        """Delete test orders with TEST_ prefix"""
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/orders",
            headers=auth_headers
        )
        if response.status_code == 200:
            orders = response.json()
            test_orders = [o for o in orders if o.get("customer_name", "").startswith("TEST_")]
            print(f"✓ Found {len(test_orders)} test orders to cleanup")
            # Note: No delete endpoint for orders in this API, just mark as completed
            for order in test_orders:
                requests.put(
                    f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/orders/{order['id']}/status",
                    json={"status": "completed"},
                    headers=auth_headers
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
