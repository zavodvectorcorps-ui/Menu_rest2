"""
Regression test suite for Restaurant Control Panel after major refactoring.
Backend server.py (1936 lines) was split into modular architecture.
Frontend MenuPage.jsx (1402 lines) was split into components.

Tests all critical API endpoints to ensure nothing is broken.
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
RESTAURANT_ID = "aa25189d-d668-4838-915a-c5d936547f3f"
PREORDER_TABLE_CODE = "6E32830E"
REGULAR_TABLE_CODE = "697DCAA5"


class TestHealthEndpoint:
    """Health endpoint - routes/seed.py"""
    
    def test_health_returns_200(self):
        """GET /api/health should return healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        print(f"✓ Health check passed: {data}")


class TestAuthEndpoints:
    """Authentication endpoints - routes/auth.py"""
    
    def test_login_with_valid_credentials(self):
        """POST /api/auth/login with admin/220066 should return access_token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "220066"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["username"] == "admin"
        assert data["user"]["role"] == "superadmin"
        assert "restaurants" in data
        print(f"✓ Login successful, got token starting with: {data['access_token'][:20]}...")
        return data["access_token"]
    
    def test_login_with_invalid_credentials(self):
        """POST /api/auth/login with wrong password should return 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid credentials correctly rejected with 401")
    
    def test_auth_me_with_token(self):
        """GET /api/auth/me with Bearer token should return user data"""
        # First login
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "220066"
        })
        token = login_response.json()["access_token"]
        
        # Then get user info
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert data["user"]["username"] == "admin"
        assert "restaurants" in data
        print(f"✓ Auth me returned user: {data['user']['username']}")
    
    def test_auth_me_without_token(self):
        """GET /api/auth/me without token should return 401"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401
        print("✓ Auth me without token correctly rejected")


class TestRestaurantEndpoints:
    """Restaurant endpoints - routes/restaurants.py"""
    
    @pytest.fixture
    def auth_headers(self):
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "220066"
        })
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_restaurants_list(self, auth_headers):
        """GET /api/restaurants should return list of restaurants"""
        response = requests.get(f"{BASE_URL}/api/restaurants", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2  # Expecting at least 2 restaurants
        restaurant_names = [r["name"] for r in data]
        assert "Мята Спортивная" in restaurant_names
        print(f"✓ Got {len(data)} restaurants: {restaurant_names}")
    
    def test_get_restaurant_by_id(self, auth_headers):
        """GET /api/restaurants/{id} should return restaurant details"""
        response = requests.get(f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == RESTAURANT_ID
        assert "name" in data
        print(f"✓ Got restaurant: {data['name']}")


class TestMenuEndpoints:
    """Menu endpoints - routes/menu.py"""
    
    @pytest.fixture
    def auth_headers(self):
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "220066"
        })
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_categories(self, auth_headers):
        """GET /api/restaurants/{id}/categories should return categories"""
        response = requests.get(f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/categories", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} categories")
        if data:
            print(f"  First category: {data[0].get('name', 'N/A')}")
    
    def test_get_menu_sections(self, auth_headers):
        """GET /api/restaurants/{id}/menu-sections should return sections"""
        response = requests.get(f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/menu-sections", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} menu sections")
    
    def test_get_menu_items(self, auth_headers):
        """GET /api/restaurants/{id}/menu-items should return items"""
        response = requests.get(f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/menu-items", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} menu items")
        if data:
            print(f"  First item: {data[0].get('name', 'N/A')} - {data[0].get('price', 0)} BYN")
    
    def test_get_labels(self, auth_headers):
        """GET /api/restaurants/{id}/labels should return labels"""
        response = requests.get(f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/labels", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} labels")


class TestTableEndpoints:
    """Table endpoints - routes/tables.py"""
    
    @pytest.fixture
    def auth_headers(self):
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "220066"
        })
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_tables(self, auth_headers):
        """GET /api/restaurants/{id}/tables should return tables"""
        response = requests.get(f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/tables", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Check for specific tables
        table_codes = [t.get("code") for t in data]
        print(f"✓ Got {len(data)} tables")
        
        # Check preorder table exists
        preorder_tables = [t for t in data if t.get("code") == PREORDER_TABLE_CODE]
        if preorder_tables:
            assert preorder_tables[0].get("is_preorder") == True
            print(f"  Preorder table {PREORDER_TABLE_CODE} found with is_preorder=True")


class TestOrderEndpoints:
    """Order endpoints - routes/orders.py"""
    
    @pytest.fixture
    def auth_headers(self):
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "220066"
        })
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_orders(self, auth_headers):
        """GET /api/restaurants/{id}/orders should return orders"""
        response = requests.get(f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/orders", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} orders")
        
        # Check if preorders are included
        preorders = [o for o in data if o.get("is_preorder")]
        print(f"  Including {len(preorders)} preorders")
    
    def test_get_staff_calls(self, auth_headers):
        """GET /api/restaurants/{id}/staff-calls should return staff calls"""
        response = requests.get(f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/staff-calls", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} staff calls")
    
    def test_get_call_types(self, auth_headers):
        """GET /api/restaurants/{id}/call-types should return call types"""
        response = requests.get(f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/call-types", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3  # Default call types
        print(f"✓ Got {len(data)} call types")
    
    def test_complete_all_orders_endpoint(self, auth_headers):
        """POST /api/restaurants/{id}/orders/complete-all should work"""
        response = requests.post(f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/orders/complete-all", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "count" in data
        print(f"✓ Complete all orders: {data['message']}")
    
    def test_complete_all_staff_calls_endpoint(self, auth_headers):
        """POST /api/restaurants/{id}/staff-calls/complete-all should work"""
        response = requests.post(f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/staff-calls/complete-all", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "count" in data
        print(f"✓ Complete all staff calls: {data['message']}")


class TestSettingsEndpoints:
    """Settings endpoints - routes/settings.py"""
    
    @pytest.fixture
    def auth_headers(self):
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "220066"
        })
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_settings(self, auth_headers):
        """GET /api/restaurants/{id}/settings should return settings"""
        response = requests.get(f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/settings", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "online_menu_enabled" in data
        assert "currency" in data
        print(f"✓ Got settings, currency: {data['currency']}")
    
    def test_get_analytics(self, auth_headers):
        """GET /api/restaurants/{id}/analytics should return analytics data"""
        response = requests.get(f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/analytics", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "views" in data
        assert "orders" in data
        assert "revenue" in data
        assert "popular_items" in data
        print(f"✓ Got analytics - Views: {data['views']['total']}, Orders: {data['orders']['total']}, Revenue: {data['revenue']['total']}")
    
    def test_get_employees(self, auth_headers):
        """GET /api/restaurants/{id}/employees should return employees"""
        response = requests.get(f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/employees", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} employees")


class TestPublicEndpoints:
    """Public endpoints - routes/public.py (no auth required)"""
    
    def test_get_public_menu_regular_table(self):
        """GET /api/public/menu/{table_code} for regular table"""
        response = requests.get(f"{BASE_URL}/api/public/menu/{REGULAR_TABLE_CODE}")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "restaurant" in data
        assert "table" in data
        assert "settings" in data
        assert "categories" in data
        assert "items" in data
        
        # Regular table should not be preorder
        table = data["table"]
        assert table.get("is_preorder") in [False, None]
        print(f"✓ Public menu for regular table {REGULAR_TABLE_CODE}")
        print(f"  Restaurant: {data['restaurant']['name']}")
        print(f"  Categories: {len(data['categories'])}, Items: {len(data['items'])}")
    
    def test_get_public_menu_preorder_table(self):
        """GET /api/public/menu/{table_code} for preorder table"""
        response = requests.get(f"{BASE_URL}/api/public/menu/{PREORDER_TABLE_CODE}")
        assert response.status_code == 200
        data = response.json()
        
        # Preorder table should have is_preorder=True
        table = data["table"]
        assert table.get("is_preorder") == True
        print(f"✓ Public menu for preorder table {PREORDER_TABLE_CODE} (is_preorder=True)")
    
    def test_get_public_menu_invalid_code(self):
        """GET /api/public/menu/INVALID should return 404"""
        response = requests.get(f"{BASE_URL}/api/public/menu/INVALID123")
        assert response.status_code == 404
        print("✓ Invalid table code correctly rejected with 404")
    
    def test_create_public_order(self):
        """POST /api/public/orders should create an order"""
        # Get menu items first
        menu_response = requests.get(f"{BASE_URL}/api/public/menu/{REGULAR_TABLE_CODE}")
        items = menu_response.json()["items"]
        
        if not items:
            pytest.skip("No menu items available for order creation")
        
        first_item = items[0]
        
        response = requests.post(f"{BASE_URL}/api/public/orders", json={
            "table_code": REGULAR_TABLE_CODE,
            "items": [{
                "menu_item_id": first_item["id"],
                "name": first_item["name"],
                "quantity": 1,
                "price": first_item["price"]
            }],
            "notes": "TEST_ORDER - Please ignore"
        })
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["status"] == "new"
        print(f"✓ Created public order: {data['id']}")
        
        # Cleanup - mark as completed so it doesn't affect other tests
        return data["id"]
    
    def test_create_public_staff_call(self):
        """POST /api/public/staff-calls should create a staff call"""
        response = requests.post(f"{BASE_URL}/api/public/staff-calls", json={
            "table_code": REGULAR_TABLE_CODE,
            "call_type_id": None  # Generic call
        })
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["status"] == "pending"
        print(f"✓ Created public staff call: {data['id']}")


class TestTelegramEndpoints:
    """Telegram endpoints - routes/telegram.py"""
    
    @pytest.fixture
    def auth_headers(self):
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "220066"
        })
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_telegram_bot_info(self, auth_headers):
        """GET /api/restaurants/{id}/telegram-bot should return bot info"""
        response = requests.get(f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/telegram-bot", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "bot_token" in data
        assert "subscribers" in data
        print(f"✓ Got telegram bot info, subscribers: {len(data['subscribers'])}")


class TestUserManagement:
    """User management endpoints - routes/auth.py"""
    
    @pytest.fixture
    def auth_headers(self):
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "220066"
        })
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_users_list(self, auth_headers):
        """GET /api/users should return users list (superadmin only)"""
        response = requests.get(f"{BASE_URL}/api/users", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # At least admin user
        
        admin_users = [u for u in data if u.get("username") == "admin"]
        assert len(admin_users) == 1
        print(f"✓ Got {len(data)} users")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
