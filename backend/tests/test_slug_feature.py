"""
Tests for custom URL (slug) feature for client menu.
Tests:
- PUT /api/restaurants/{id} - slug saving, validation (uniqueness, format)
- GET /api/public/menu-by-slug/{slug}/{table_number} - returns menu data
- QR code generation with slug URL when restaurant has slug
"""

import pytest
import requests
import os
import re

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "admin",
        "password": "220066"
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Auth headers for API requests"""
    return {"Authorization": f"Bearer {auth_token}"}


# Restaurant IDs from test context
RESTAURANT_WITH_SLUG = "aa25189d-d668-4838-915a-c5d936547f3f"
RESTAURANT_WITHOUT_SLUG = "d433dc80-02e6-41ca-9527-df7f78f4b4aa"
EXISTING_SLUG = "myata-sport"


class TestPublicMenuBySlug:
    """Test GET /api/public/menu-by-slug/{slug}/{table_number}"""
    
    def test_get_menu_by_slug_success(self):
        """Menu loads via slug URL with valid slug and table number"""
        response = requests.get(f"{BASE_URL}/api/public/menu-by-slug/{EXISTING_SLUG}/1")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "restaurant" in data
        assert "table" in data
        assert "settings" in data
        assert "sections" in data
        assert "categories" in data
        assert "items" in data
        assert "call_types" in data
        
        # Verify restaurant has the slug
        assert data["restaurant"]["slug"] == EXISTING_SLUG
        assert data["restaurant"]["id"] == RESTAURANT_WITH_SLUG
        
        # Verify table data
        assert data["table"]["number"] == 1
        assert "code" in data["table"]  # table_code needed for orders/calls
        print(f"✓ Menu loaded via slug '{EXISTING_SLUG}' for table #1")
    
    def test_get_menu_by_slug_invalid_slug(self):
        """Returns 404 for non-existent slug"""
        response = requests.get(f"{BASE_URL}/api/public/menu-by-slug/non-existent-restaurant/1")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        assert "Ресторан не найден" in response.json().get("detail", "")
        print("✓ 404 returned for invalid slug")
    
    def test_get_menu_by_slug_invalid_table(self):
        """Returns 404 for non-existent table number"""
        response = requests.get(f"{BASE_URL}/api/public/menu-by-slug/{EXISTING_SLUG}/999")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        assert "Стол не найден" in response.json().get("detail", "")
        print("✓ 404 returned for invalid table number")
    
    def test_get_menu_by_slug_table_zero_preorder(self):
        """Table #0 (preorder table) should be accessible via slug"""
        response = requests.get(f"{BASE_URL}/api/public/menu-by-slug/{EXISTING_SLUG}/0")
        
        # Preorder table (number 0) should exist
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["table"]["number"] == 0
        assert data["table"].get("is_preorder", False) == True
        print("✓ Preorder table (0) accessible via slug")


class TestSlugSaveAndValidation:
    """Test PUT /api/restaurants/{id} - slug field"""
    
    def test_get_restaurant_with_slug(self, auth_headers):
        """Verify restaurant has slug field in response"""
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_WITH_SLUG}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "slug" in data
        assert data["slug"] == EXISTING_SLUG
        print(f"✓ Restaurant has slug: {data['slug']}")
    
    def test_update_slug_valid_format(self, auth_headers):
        """Update slug with valid format (letters, numbers, hyphens)"""
        # Update to a new slug
        new_slug = "test-slug-123"
        response = requests.put(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_WITH_SLUG}",
            headers=auth_headers,
            json={"slug": new_slug}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["slug"] == new_slug
        print(f"✓ Slug updated to: {new_slug}")
        
        # Restore original slug
        response = requests.put(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_WITH_SLUG}",
            headers=auth_headers,
            json={"slug": EXISTING_SLUG}
        )
        assert response.status_code == 200
        print(f"✓ Slug restored to: {EXISTING_SLUG}")
    
    def test_update_slug_invalid_format_uppercase(self, auth_headers):
        """Slug with uppercase should be converted to lowercase"""
        response = requests.put(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_WITH_SLUG}",
            headers=auth_headers,
            json={"slug": "TEST-UPPER"}
        )
        
        # Backend should lowercase the slug
        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == "test-upper"
        print("✓ Uppercase slug converted to lowercase")
        
        # Restore original
        requests.put(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_WITH_SLUG}",
            headers=auth_headers,
            json={"slug": EXISTING_SLUG}
        )
    
    def test_update_slug_invalid_chars(self, auth_headers):
        """Slug with invalid characters should be rejected"""
        response = requests.put(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_WITH_SLUG}",
            headers=auth_headers,
            json={"slug": "test_invalid!"}
        )
        
        # Should reject due to invalid characters (underscore, exclamation)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Invalid characters in slug rejected")
    
    def test_update_slug_cyrillic(self, auth_headers):
        """Slug with Cyrillic characters should be rejected"""
        response = requests.put(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_WITH_SLUG}",
            headers=auth_headers,
            json={"slug": "мята-ресторан"}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Cyrillic slug rejected")
    
    def test_update_slug_uniqueness(self, auth_headers):
        """Slug must be unique across restaurants"""
        # Try to set second restaurant's slug to existing slug
        response = requests.put(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_WITHOUT_SLUG}",
            headers=auth_headers,
            json={"slug": EXISTING_SLUG}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        assert "занят" in response.json().get("detail", "").lower()
        print("✓ Duplicate slug rejected")
    
    def test_update_slug_empty_allowed(self, auth_headers):
        """Empty slug should be allowed (removes slug)"""
        # Set slug to empty
        response = requests.put(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_WITHOUT_SLUG}",
            headers=auth_headers,
            json={"slug": ""}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("slug", "") == ""
        print("✓ Empty slug allowed")
    
    def test_update_slug_single_char(self, auth_headers):
        """Single character slug should be valid"""
        response = requests.put(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_WITHOUT_SLUG}",
            headers=auth_headers,
            json={"slug": "x"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == "x"
        print("✓ Single char slug accepted")
        
        # Clean up - remove slug
        requests.put(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_WITHOUT_SLUG}",
            headers=auth_headers,
            json={"slug": ""}
        )


class TestQRCodeWithSlug:
    """Test QR code generation uses slug-based URL when available"""
    
    def test_qr_code_with_slug(self, auth_headers):
        """QR code endpoint returns slug-based URL for restaurant with slug"""
        # Get tables first
        tables_response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_WITH_SLUG}/tables",
            headers=auth_headers
        )
        assert tables_response.status_code == 200
        tables = tables_response.json()
        table = next((t for t in tables if t["number"] == 1), None)
        assert table is not None, "Table #1 not found"
        
        # Get QR code
        base_url = "https://order-hub-pro-5.preview.emergentagent.com"
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_WITH_SLUG}/tables/{table['id']}/qr?base_url={base_url}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "menu_url" in data
        assert "qr_base64" in data
        
        # URL should use slug format: /{slug}/{table_number}
        expected_url = f"{base_url}/{EXISTING_SLUG}/{table['number']}"
        assert data["menu_url"] == expected_url, f"Expected {expected_url}, got {data['menu_url']}"
        print(f"✓ QR code URL: {data['menu_url']}")
    
    def test_qr_code_without_slug(self, auth_headers):
        """QR code endpoint returns code-based URL for restaurant without slug"""
        # First ensure restaurant without slug has no slug
        requests.put(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_WITHOUT_SLUG}",
            headers=auth_headers,
            json={"slug": ""}
        )
        
        # Get tables
        tables_response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_WITHOUT_SLUG}/tables",
            headers=auth_headers
        )
        
        if tables_response.status_code != 200 or not tables_response.json():
            pytest.skip("No tables found for second restaurant")
        
        tables = tables_response.json()
        table = tables[0]
        
        # Get QR code
        base_url = "https://order-hub-pro-5.preview.emergentagent.com"
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_WITHOUT_SLUG}/tables/{table['id']}/qr?base_url={base_url}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # URL should use code format: /menu/{code}
        expected_url = f"{base_url}/menu/{table['code']}"
        assert data["menu_url"] == expected_url, f"Expected {expected_url}, got {data['menu_url']}"
        print(f"✓ QR code URL (no slug): {data['menu_url']}")


class TestOldMenuFormatStillWorks:
    """Test that old /menu/{code} format still works"""
    
    def test_old_menu_format_works(self):
        """GET /api/public/menu/{table_code} still returns menu"""
        table_code = "697DCAA5"  # Table #1 code
        response = requests.get(f"{BASE_URL}/api/public/menu/{table_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "restaurant" in data
        assert "table" in data
        assert data["table"]["code"] == table_code
        print(f"✓ Old format /menu/{table_code} still works")


class TestOrdersAndCallsViaSlugMenu:
    """Test that orders and staff calls work when accessing menu via slug"""
    
    def test_create_order_via_slug_menu(self):
        """Order created via slug menu uses correct table_code"""
        # First get menu via slug to get table code
        menu_response = requests.get(f"{BASE_URL}/api/public/menu-by-slug/{EXISTING_SLUG}/1")
        assert menu_response.status_code == 200
        menu_data = menu_response.json()
        
        table_code = menu_data["table"]["code"]
        
        # Get a menu item to order
        items = menu_data.get("items", [])
        if not items:
            pytest.skip("No menu items available")
        
        item = items[0]
        
        # Create order using table_code from API response
        order_response = requests.post(f"{BASE_URL}/api/public/orders", json={
            "table_code": table_code,
            "items": [{
                "menu_item_id": item["id"],
                "name": item["name"],
                "quantity": 1,
                "price": item["price"]
            }],
            "notes": "TEST_order_via_slug"
        })
        
        assert order_response.status_code == 200, f"Order failed: {order_response.text}"
        order_data = order_response.json()
        assert "id" in order_data
        assert order_data["table_number"] == 1
        print(f"✓ Order created via slug menu, order_id: {order_data['id']}")
    
    def test_staff_call_via_slug_menu(self):
        """Staff call works via slug menu"""
        # Get menu via slug
        menu_response = requests.get(f"{BASE_URL}/api/public/menu-by-slug/{EXISTING_SLUG}/1")
        assert menu_response.status_code == 200
        menu_data = menu_response.json()
        
        table_code = menu_data["table"]["code"]
        call_types = menu_data.get("call_types", [])
        
        if not call_types:
            pytest.skip("No call types available")
        
        call_type = call_types[0]
        
        # Create staff call
        call_response = requests.post(f"{BASE_URL}/api/public/staff-calls", json={
            "table_code": table_code,
            "call_type_id": call_type["id"]
        })
        
        assert call_response.status_code == 200, f"Staff call failed: {call_response.text}"
        call_data = call_response.json()
        assert "id" in call_data
        assert call_data["table_number"] == 1
        print(f"✓ Staff call created via slug menu, call_id: {call_data['id']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
