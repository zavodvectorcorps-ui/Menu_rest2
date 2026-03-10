"""
Backend API Tests for Restaurant Dashboard - Authentication and Import features
Tests: Login, Auth, Categories CRUD with auth, Menu Items CRUD with auth, JSON Import, Tables, Analytics
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Restaurant IDs from seed data
RESTAURANT_ID_1 = "aa25189d-d668-4838-915a-c5d936547f3f"  # Мята Спортивная Тест
RESTAURANT_ID_2 = "d433dc80-02e6-41ca-9527-df7f78f4b4aa"  # Мята Центральная


class TestAuth:
    """Authentication endpoint tests - login, /me with JWT"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before tests"""
        self.auth_token = None
        self.user = None
        self.restaurants = []
        
        # Login with superadmin
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "220066"
        })
        if response.status_code == 200:
            data = response.json()
            self.auth_token = data.get("access_token")
            self.user = data.get("user")
            self.restaurants = data.get("restaurants", [])
    
    def test_login_success(self):
        """Test POST /api/auth/login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "220066"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "access_token" in data
        assert "token_type" in data
        assert "user" in data
        assert "restaurants" in data
        
        # Verify token type
        assert data["token_type"] == "bearer"
        
        # Verify user structure
        user = data["user"]
        assert "id" in user
        assert user["username"] == "admin"
        assert user["role"] == "superadmin"
        
        # Verify restaurants list
        assert isinstance(data["restaurants"], list)
        print(f"Login successful - Got {len(data['restaurants'])} restaurants")
    
    def test_login_invalid_password(self):
        """Test POST /api/auth/login with invalid password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        print(f"Login rejection correct: {data['detail']}")
    
    def test_login_invalid_username(self):
        """Test POST /api/auth/login with invalid username"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "nonexistent",
            "password": "220066"
        })
        
        assert response.status_code == 401
    
    def test_auth_me_with_valid_token(self):
        """Test GET /api/auth/me with valid Bearer token"""
        assert self.auth_token, "Auth token not available"
        
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {self.auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "user" in data
        assert "restaurants" in data
        
        # Verify user data
        user = data["user"]
        assert user["username"] == "admin"
        assert user["role"] == "superadmin"
        
        print(f"/me endpoint returns user: {user['username']} with {len(data['restaurants'])} restaurants")
    
    def test_auth_me_without_token(self):
        """Test GET /api/auth/me without Bearer token returns 401"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        
        assert response.status_code == 401
    
    def test_auth_me_with_invalid_token(self):
        """Test GET /api/auth/me with invalid Bearer token returns 401"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": "Bearer invalid_token_123"}
        )
        
        assert response.status_code == 401


class TestRestaurantsWithAuth:
    """Restaurant list endpoint tests with authentication"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before tests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "220066"
        })
        if response.status_code == 200:
            self.auth_token = response.json().get("access_token")
        else:
            self.auth_token = None
    
    def test_get_restaurants_with_auth(self):
        """Test GET /api/restaurants with valid auth returns list"""
        assert self.auth_token, "Auth token not available"
        
        response = requests.get(
            f"{BASE_URL}/api/restaurants",
            headers={"Authorization": f"Bearer {self.auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Verify restaurant structure
        for restaurant in data:
            assert "id" in restaurant
            assert "name" in restaurant
        
        print(f"Got {len(data)} restaurants")
    
    def test_get_restaurants_without_auth(self):
        """Test GET /api/restaurants without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/restaurants")
        
        assert response.status_code == 401


class TestCategoriesCRUDWithAuth:
    """Categories CRUD tests with authentication"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token and restaurant ID before tests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "220066"
        })
        if response.status_code == 200:
            data = response.json()
            self.auth_token = data.get("access_token")
            restaurants = data.get("restaurants", [])
            self.restaurant_id = restaurants[0]["id"] if restaurants else None
        else:
            self.auth_token = None
            self.restaurant_id = None
        
        self.headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
    
    def test_get_categories(self):
        """Test GET /api/restaurants/{id}/categories returns categories list"""
        assert self.auth_token, "Auth token not available"
        assert self.restaurant_id, "Restaurant ID not available"
        
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/categories",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        
        # Verify category structure if any exist
        for cat in data:
            assert "id" in cat
            assert "name" in cat
            assert "restaurant_id" in cat
        
        print(f"Got {len(data)} categories for restaurant {self.restaurant_id}")
    
    def test_create_category(self):
        """Test POST /api/restaurants/{id}/categories creates a category"""
        assert self.auth_token, "Auth token not available"
        assert self.restaurant_id, "Restaurant ID not available"
        
        test_name = f"TEST_Cat_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": test_name,
            "sort_order": 99,
            "is_active": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/categories",
            json=payload,
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == test_name
        assert data["restaurant_id"] == self.restaurant_id
        assert "id" in data
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/categories/{data['id']}",
            headers=self.headers
        )
        print(f"Created and cleaned up category: {test_name}")
    
    def test_update_category(self):
        """Test PUT /api/restaurants/{id}/categories/{cat_id} updates a category"""
        assert self.auth_token, "Auth token not available"
        assert self.restaurant_id, "Restaurant ID not available"
        
        # Create test category
        test_name = f"TEST_CatUpdate_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/categories",
            json={"name": test_name, "sort_order": 50, "is_active": True},
            headers=self.headers
        )
        cat_id = create_response.json()["id"]
        
        # Update category
        updated_name = f"TEST_CatUpdated_{uuid.uuid4().hex[:8]}"
        update_response = requests.put(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/categories/{cat_id}",
            json={"name": updated_name, "sort_order": 51, "is_active": False},
            headers=self.headers
        )
        
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["name"] == updated_name
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/categories/{cat_id}",
            headers=self.headers
        )
        print(f"Updated category: {test_name} -> {updated_name}")
    
    def test_delete_category(self):
        """Test DELETE /api/restaurants/{id}/categories/{cat_id} removes a category"""
        assert self.auth_token, "Auth token not available"
        assert self.restaurant_id, "Restaurant ID not available"
        
        # Create test category
        test_name = f"TEST_CatDelete_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/categories",
            json={"name": test_name, "sort_order": 100, "is_active": True},
            headers=self.headers
        )
        cat_id = create_response.json()["id"]
        
        # Delete category
        delete_response = requests.delete(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/categories/{cat_id}",
            headers=self.headers
        )
        
        assert delete_response.status_code == 200
        
        # Verify deletion
        get_response = requests.get(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/categories",
            headers=self.headers
        )
        cat_ids = [c["id"] for c in get_response.json()]
        assert cat_id not in cat_ids
        print(f"Deleted category: {test_name}")


class TestMenuItemsCRUDWithAuth:
    """Menu Items CRUD tests with authentication"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token, restaurant ID, and a category ID before tests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "220066"
        })
        if response.status_code == 200:
            data = response.json()
            self.auth_token = data.get("access_token")
            restaurants = data.get("restaurants", [])
            self.restaurant_id = restaurants[0]["id"] if restaurants else None
        else:
            self.auth_token = None
            self.restaurant_id = None
        
        self.headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
        
        # Get or create a category for items
        self.category_id = None
        if self.restaurant_id:
            cat_response = requests.get(
                f"{BASE_URL}/api/restaurants/{self.restaurant_id}/categories",
                headers=self.headers
            )
            categories = cat_response.json()
            if categories:
                self.category_id = categories[0]["id"]
    
    def test_get_menu_items(self):
        """Test GET /api/restaurants/{id}/menu-items returns items list"""
        assert self.auth_token, "Auth token not available"
        assert self.restaurant_id, "Restaurant ID not available"
        
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/menu-items",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        print(f"Got {len(data)} menu items")
    
    def test_create_menu_item(self):
        """Test POST /api/restaurants/{id}/menu-items creates a menu item"""
        assert self.auth_token, "Auth token not available"
        assert self.restaurant_id, "Restaurant ID not available"
        
        # Create category if none exists
        category_id = self.category_id
        if not category_id:
            cat_response = requests.post(
                f"{BASE_URL}/api/restaurants/{self.restaurant_id}/categories",
                json={"name": f"TEST_ItemCat_{uuid.uuid4().hex[:8]}", "sort_order": 0, "is_active": True},
                headers=self.headers
            )
            category_id = cat_response.json()["id"]
        
        test_name = f"TEST_Item_{uuid.uuid4().hex[:8]}"
        payload = {
            "category_id": category_id,
            "name": test_name,
            "description": "Test item description",
            "price": 15.50,
            "is_available": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/menu-items",
            json=payload,
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == test_name
        assert data["price"] == 15.50
        assert data["category_id"] == category_id
        assert "id" in data
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/menu-items/{data['id']}",
            headers=self.headers
        )
        print(f"Created and cleaned up menu item: {test_name}")
    
    def test_update_menu_item(self):
        """Test PUT /api/restaurants/{id}/menu-items/{item_id} updates an item"""
        assert self.auth_token, "Auth token not available"
        assert self.restaurant_id, "Restaurant ID not available"
        
        # Create category if none exists
        category_id = self.category_id
        if not category_id:
            cat_response = requests.post(
                f"{BASE_URL}/api/restaurants/{self.restaurant_id}/categories",
                json={"name": f"TEST_ItemCat2_{uuid.uuid4().hex[:8]}", "sort_order": 0, "is_active": True},
                headers=self.headers
            )
            category_id = cat_response.json()["id"]
        
        # Create test item
        test_name = f"TEST_ItemUpdate_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/menu-items",
            json={"category_id": category_id, "name": test_name, "price": 10.0, "is_available": True},
            headers=self.headers
        )
        item_id = create_response.json()["id"]
        
        # Update item
        update_response = requests.put(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/menu-items/{item_id}",
            json={"name": "Updated Name", "price": 20.0},
            headers=self.headers
        )
        
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["name"] == "Updated Name"
        assert data["price"] == 20.0
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/menu-items/{item_id}",
            headers=self.headers
        )
        print(f"Updated menu item: {test_name}")
    
    def test_delete_menu_item(self):
        """Test DELETE /api/restaurants/{id}/menu-items/{item_id} removes an item"""
        assert self.auth_token, "Auth token not available"
        assert self.restaurant_id, "Restaurant ID not available"
        
        # Create category if none exists
        category_id = self.category_id
        if not category_id:
            cat_response = requests.post(
                f"{BASE_URL}/api/restaurants/{self.restaurant_id}/categories",
                json={"name": f"TEST_ItemCat3_{uuid.uuid4().hex[:8]}", "sort_order": 0, "is_active": True},
                headers=self.headers
            )
            category_id = cat_response.json()["id"]
        
        # Create test item
        test_name = f"TEST_ItemDelete_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/menu-items",
            json={"category_id": category_id, "name": test_name, "price": 5.0, "is_available": True},
            headers=self.headers
        )
        item_id = create_response.json()["id"]
        
        # Delete item
        delete_response = requests.delete(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/menu-items/{item_id}",
            headers=self.headers
        )
        
        assert delete_response.status_code == 200
        print(f"Deleted menu item: {test_name}")


class TestJSONImport:
    """JSON Import endpoint tests - POST /api/restaurants/{id}/import-menu"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token and restaurant ID before tests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "220066"
        })
        if response.status_code == 200:
            data = response.json()
            self.auth_token = data.get("access_token")
            restaurants = data.get("restaurants", [])
            self.restaurant_id = restaurants[0]["id"] if restaurants else None
        else:
            self.auth_token = None
            self.restaurant_id = None
        
        self.headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
    
    def test_import_menu_simple(self):
        """Test POST /api/restaurants/{id}/import-menu imports categories and items"""
        assert self.auth_token, "Auth token not available"
        assert self.restaurant_id, "Restaurant ID not available"
        
        test_category_name = f"TEST_ImportCat_{uuid.uuid4().hex[:8]}"
        test_item_name = f"TEST_ImportItem_{uuid.uuid4().hex[:8]}"
        
        import_data = {
            "data": {
                "categories": [
                    {
                        "name": test_category_name,
                        "items": [
                            {"name": test_item_name, "price": 10.50, "description": "Imported item"}
                        ]
                    }
                ]
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/import-menu",
            json=import_data,
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "imported_categories" in data
        assert "imported_items" in data
        assert data["imported_categories"] >= 1
        assert data["imported_items"] >= 1
        
        print(f"Import result: {data['imported_categories']} categories, {data['imported_items']} items")
        
        # Verify data was actually imported
        cat_response = requests.get(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/categories",
            headers=self.headers
        )
        categories = cat_response.json()
        cat_names = [c["name"] for c in categories]
        assert test_category_name in cat_names
        
        items_response = requests.get(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/menu-items",
            headers=self.headers
        )
        items = items_response.json()
        item_names = [i["name"] for i in items]
        assert test_item_name in item_names
        
        # Cleanup - find and delete test category and items
        test_cat = next((c for c in categories if c["name"] == test_category_name), None)
        if test_cat:
            # Delete items in category first
            for item in items:
                if item["name"] == test_item_name:
                    requests.delete(
                        f"{BASE_URL}/api/restaurants/{self.restaurant_id}/menu-items/{item['id']}",
                        headers=self.headers
                    )
            # Delete category
            requests.delete(
                f"{BASE_URL}/api/restaurants/{self.restaurant_id}/categories/{test_cat['id']}",
                headers=self.headers
            )
        
        print(f"Import test completed and cleaned up")
    
    def test_import_menu_multiple_categories(self):
        """Test import with multiple categories and items"""
        assert self.auth_token, "Auth token not available"
        assert self.restaurant_id, "Restaurant ID not available"
        
        unique_id = uuid.uuid4().hex[:8]
        import_data = {
            "data": {
                "categories": [
                    {
                        "name": f"TEST_MultiCat1_{unique_id}",
                        "items": [
                            {"name": f"TEST_Item1_{unique_id}", "price": 5.0},
                            {"name": f"TEST_Item2_{unique_id}", "price": 7.5}
                        ]
                    },
                    {
                        "name": f"TEST_MultiCat2_{unique_id}",
                        "items": [
                            {"name": f"TEST_Item3_{unique_id}", "price": 12.0}
                        ]
                    }
                ]
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/import-menu",
            json=import_data,
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["imported_categories"] >= 2
        assert data["imported_items"] >= 3
        
        print(f"Multi-category import: {data['imported_categories']} categories, {data['imported_items']} items")
        
        # Cleanup
        cat_response = requests.get(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/categories",
            headers=self.headers
        )
        for cat in cat_response.json():
            if unique_id in cat["name"]:
                requests.delete(
                    f"{BASE_URL}/api/restaurants/{self.restaurant_id}/categories/{cat['id']}",
                    headers=self.headers
                )
    
    def test_import_menu_without_auth(self):
        """Test import without auth returns 401"""
        assert self.restaurant_id, "Restaurant ID not available"
        
        import_data = {"data": {"categories": [{"name": "Test", "items": []}]}}
        
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/import-menu",
            json=import_data
        )
        
        assert response.status_code == 401


class TestTablesWithAuth:
    """Tables management tests with authentication"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token and restaurant ID before tests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "220066"
        })
        if response.status_code == 200:
            data = response.json()
            self.auth_token = data.get("access_token")
            restaurants = data.get("restaurants", [])
            self.restaurant_id = restaurants[0]["id"] if restaurants else None
        else:
            self.auth_token = None
            self.restaurant_id = None
        
        self.headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
    
    def test_get_tables(self):
        """Test GET /api/restaurants/{id}/tables returns tables list"""
        assert self.auth_token, "Auth token not available"
        assert self.restaurant_id, "Restaurant ID not available"
        
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/tables",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        
        # Verify table structure
        for table in data:
            assert "id" in table
            assert "number" in table
            assert "code" in table
            assert "is_active" in table
        
        print(f"Got {len(data)} tables")
    
    def test_get_tables_without_auth(self):
        """Test GET /api/restaurants/{id}/tables without auth returns 401"""
        assert self.restaurant_id, "Restaurant ID not available"
        
        response = requests.get(f"{BASE_URL}/api/restaurants/{self.restaurant_id}/tables")
        
        assert response.status_code == 401


class TestAnalytics:
    """Analytics endpoint tests with authentication"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token and restaurant ID before tests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "220066"
        })
        if response.status_code == 200:
            data = response.json()
            self.auth_token = data.get("access_token")
            restaurants = data.get("restaurants", [])
            self.restaurant_id = restaurants[0]["id"] if restaurants else None
        else:
            self.auth_token = None
            self.restaurant_id = None
        
        self.headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
    
    def test_get_analytics(self):
        """Test GET /api/restaurants/{id}/analytics returns analytics data"""
        assert self.auth_token, "Auth token not available"
        assert self.restaurant_id, "Restaurant ID not available"
        
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/analytics",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify analytics structure
        assert "period_days" in data
        assert "views" in data
        assert "orders" in data
        assert "revenue" in data
        assert "staff_calls" in data
        
        # Verify views structure
        views = data["views"]
        assert "total" in views
        assert "today" in views
        assert "by_day" in views
        
        # Verify orders structure
        orders = data["orders"]
        assert "total" in orders
        assert "today" in orders
        assert "by_day" in orders
        
        print(f"Analytics: {views['total']} views, {orders['total']} orders, {data['revenue']['total']} revenue")
    
    def test_get_analytics_without_auth(self):
        """Test GET /api/restaurants/{id}/analytics without auth returns 401"""
        assert self.restaurant_id, "Restaurant ID not available"
        
        response = requests.get(f"{BASE_URL}/api/restaurants/{self.restaurant_id}/analytics")
        
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
