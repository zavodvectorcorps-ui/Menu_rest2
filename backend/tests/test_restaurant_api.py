"""
Backend API Tests for Restaurant Dashboard
Tests: Menu Sections, Call Types, Public Menu, Categories, Settings, Image Upload, QR Code
NOTE: These tests require authentication - use JWT tokens and restaurant_id prefix
"""
import pytest
import requests
import os
import uuid
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


def get_auth_headers():
    """Login and get auth headers"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "admin",
        "password": "220066"
    })
    if response.status_code == 200:
        data = response.json()
        return {
            "headers": {"Authorization": f"Bearer {data['access_token']}"},
            "restaurant_id": data["restaurants"][0]["id"] if data["restaurants"] else None
        }
    return {"headers": {}, "restaurant_id": None}


class TestMenuSections:
    """Menu Sections CRUD tests - Еда, Напитки, Кальяны"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        auth = get_auth_headers()
        self.headers = auth["headers"]
        self.restaurant_id = auth["restaurant_id"]
    
    def test_get_menu_sections(self):
        """Test GET /api/restaurants/{id}/menu-sections returns sections"""
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/menu-sections",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3  # At least food, drinks, hookah
        
        # Verify section structure
        section_names = [s['name'] for s in data]
        assert 'Еда' in section_names
        assert 'Напитки' in section_names
        assert 'Кальяны' in section_names
    
    def test_create_menu_section(self):
        """Test POST /api/restaurants/{id}/menu-sections creates new section"""
        test_name = f"TEST_Section_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": test_name,
            "sort_order": 99,
            "is_active": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/menu-sections",
            json=payload,
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data['name'] == test_name
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/menu-sections/{data['id']}",
            headers=self.headers
        )
    
    def test_update_menu_section(self):
        """Test PUT /api/restaurants/{id}/menu-sections/{id} updates section"""
        test_name = f"TEST_Update_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/menu-sections",
            json={"name": test_name, "sort_order": 50, "is_active": True},
            headers=self.headers
        )
        section_id = create_response.json()['id']
        
        updated_name = f"TEST_Updated_{uuid.uuid4().hex[:8]}"
        update_response = requests.put(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/menu-sections/{section_id}",
            json={"name": updated_name, "sort_order": 51, "is_active": False},
            headers=self.headers
        )
        assert update_response.status_code == 200
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/menu-sections/{section_id}",
            headers=self.headers
        )
    
    def test_delete_menu_section(self):
        """Test DELETE /api/restaurants/{id}/menu-sections/{id} removes section"""
        test_name = f"TEST_Delete_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/menu-sections",
            json={"name": test_name, "sort_order": 100, "is_active": True},
            headers=self.headers
        )
        section_id = create_response.json()['id']
        
        delete_response = requests.delete(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/menu-sections/{section_id}",
            headers=self.headers
        )
        assert delete_response.status_code == 200


class TestCallTypes:
    """Call Types CRUD tests - Официант, Кальянный мастер, Счёт"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        auth = get_auth_headers()
        self.headers = auth["headers"]
        self.restaurant_id = auth["restaurant_id"]
    
    def test_get_call_types(self):
        """Test GET /api/restaurants/{id}/call-types returns call types"""
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/call-types",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3
        
        call_names = [ct['name'] for ct in data]
        assert 'Вызов официанта' in call_names
        assert 'Вызов кальянного мастера' in call_names
        assert 'Попросить счёт' in call_names
    
    def test_create_call_type(self):
        """Test POST /api/restaurants/{id}/call-types creates new call type"""
        test_name = f"TEST_CallType_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": test_name,
            "telegram_message": "🔔 Test call",
            "sort_order": 99,
            "is_active": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/call-types",
            json=payload,
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data['name'] == test_name
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/call-types/{data['id']}",
            headers=self.headers
        )


class TestPublicMenu:
    """Public Menu endpoint tests - /api/public/menu/{table_code} (NO AUTH)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        # Get a valid table code first
        auth = get_auth_headers()
        tables_response = requests.get(
            f"{BASE_URL}/api/restaurants/{auth['restaurant_id']}/tables",
            headers=auth["headers"]
        )
        tables = tables_response.json()
        self.table_code = tables[0]['code'] if tables else None
    
    def test_get_public_menu_valid_table(self):
        """Test GET /api/public/menu/{table_code} returns full menu data"""
        if not self.table_code:
            pytest.skip("No tables available")
        
        response = requests.get(f"{BASE_URL}/api/public/menu/{self.table_code}")
        assert response.status_code == 200
        
        data = response.json()
        assert 'table' in data
        assert 'restaurant' in data
        assert 'settings' in data
        assert 'sections' in data
        assert 'categories' in data
        assert 'items' in data
        assert 'call_types' in data
    
    def test_get_public_menu_invalid_table(self):
        """Test GET /api/public/menu/{invalid_code} returns 404"""
        response = requests.get(f"{BASE_URL}/api/public/menu/INVALID123")
        assert response.status_code == 404


class TestCategories:
    """Categories CRUD tests with auth"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        auth = get_auth_headers()
        self.headers = auth["headers"]
        self.restaurant_id = auth["restaurant_id"]
    
    def test_get_categories(self):
        """Test GET /api/restaurants/{id}/categories returns categories"""
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/categories",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
    
    def test_create_category(self):
        """Test POST /api/restaurants/{id}/categories creates category"""
        test_name = f"TEST_Category_{uuid.uuid4().hex[:8]}"
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
        assert data['name'] == test_name
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/categories/{data['id']}",
            headers=self.headers
        )


class TestSettings:
    """Settings tests with auth"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        auth = get_auth_headers()
        self.headers = auth["headers"]
        self.restaurant_id = auth["restaurant_id"]
    
    def test_get_settings(self):
        """Test GET /api/restaurants/{id}/settings returns settings"""
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/settings",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert 'currency' in data
        assert data['currency'] == 'BYN'
        assert 'telegram_bot_token' in data
        assert 'telegram_chat_id' in data
    
    def test_update_telegram_settings(self):
        """Test PUT /api/restaurants/{id}/settings can update telegram settings"""
        get_response = requests.get(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/settings",
            headers=self.headers
        )
        original_settings = get_response.json()
        
        test_token = "TEST_TOKEN_123"
        test_chat_id = "-1001234567890"
        
        update_response = requests.put(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/settings",
            json={"telegram_bot_token": test_token, "telegram_chat_id": test_chat_id},
            headers=self.headers
        )
        assert update_response.status_code == 200
        
        # Restore original settings
        requests.put(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/settings",
            json={
                "telegram_bot_token": original_settings.get('telegram_bot_token', ''),
                "telegram_chat_id": original_settings.get('telegram_chat_id', '')
            },
            headers=self.headers
        )


class TestPublicStaffCalls:
    """Public Staff calls tests (NO AUTH)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        auth = get_auth_headers()
        # Get table code
        tables_response = requests.get(
            f"{BASE_URL}/api/restaurants/{auth['restaurant_id']}/tables",
            headers=auth["headers"]
        )
        tables = tables_response.json()
        self.table_code = tables[0]['code'] if tables else None
        
        # Get call types
        ct_response = requests.get(
            f"{BASE_URL}/api/restaurants/{auth['restaurant_id']}/call-types",
            headers=auth["headers"]
        )
        call_types = ct_response.json()
        self.waiter_ct = next((ct for ct in call_types if 'официант' in ct['name'].lower()), None)
    
    def test_create_staff_call_with_type(self):
        """Test POST /api/public/staff-calls creates call with call_type_id"""
        if not self.table_code or not self.waiter_ct:
            pytest.skip("Missing table code or call type")
        
        payload = {
            "table_code": self.table_code,
            "call_type_id": self.waiter_ct['id']
        }
        
        response = requests.post(f"{BASE_URL}/api/public/staff-calls", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data['call_type_id'] == self.waiter_ct['id']
        assert data['call_type_name'] == self.waiter_ct['name']


class TestMenuItems:
    """Menu items tests with auth"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        auth = get_auth_headers()
        self.headers = auth["headers"]
        self.restaurant_id = auth["restaurant_id"]
        
        # Get a category for items
        cat_response = requests.get(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/categories",
            headers=self.headers
        )
        categories = cat_response.json()
        self.category_id = categories[0]['id'] if categories else None
    
    def test_get_menu_items(self):
        """Test GET /api/restaurants/{id}/menu-items returns items"""
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/menu-items",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
    
    def test_create_banner_item(self):
        """Test POST /api/restaurants/{id}/menu-items can create banner"""
        if not self.category_id:
            pytest.skip("No categories available")
        
        test_name = f"TEST_Banner_{uuid.uuid4().hex[:8]}"
        payload = {
            "category_id": self.category_id,
            "name": test_name,
            "description": "Test banner description",
            "price": 0,
            "is_banner": True,
            "is_available": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/menu-items",
            json=payload,
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data['is_banner'] == True
        assert data['price'] == 0
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/menu-items/{data['id']}",
            headers=self.headers
        )


class TestImageUpload:
    """Image upload endpoint tests - POST /api/upload"""
    
    def test_upload_valid_image(self):
        """Test POST /api/upload with valid PNG image"""
        # Create a minimal valid PNG file
        png_header = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
        
        files = {'file': ('test.png', io.BytesIO(png_header), 'image/png')}
        response = requests.post(f"{BASE_URL}/api/upload", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert 'url' in data
        assert 'filename' in data
        assert data['url'].startswith('/uploads/')
    
    def test_upload_invalid_file_type(self):
        """Test POST /api/upload rejects non-image files"""
        files = {'file': ('test.txt', io.BytesIO(b'test content'), 'text/plain')}
        response = requests.post(f"{BASE_URL}/api/upload", files=files)
        
        assert response.status_code == 400


class TestQRCode:
    """QR code generation endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        auth = get_auth_headers()
        self.headers = auth["headers"]
        self.restaurant_id = auth["restaurant_id"]
        
        # Get a valid table
        tables_response = requests.get(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/tables",
            headers=self.headers
        )
        tables = tables_response.json()
        if tables:
            self.table_id = tables[0]['id']
            self.table_code = tables[0]['code']
        else:
            self.table_id = None
            self.table_code = None
    
    def test_get_qr_code_valid_table(self):
        """Test GET /api/restaurants/{id}/tables/{table_id}/qr returns QR code"""
        if not self.table_id:
            pytest.skip("No tables available")
        
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/tables/{self.table_id}/qr",
            params={"base_url": BASE_URL},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'table_id' in data
        assert 'table_number' in data
        assert 'table_code' in data
        assert 'menu_url' in data
        assert 'qr_base64' in data
        assert data['qr_base64'].startswith('data:image/png;base64,')
    
    def test_get_qr_code_invalid_table(self):
        """Test GET /api/restaurants/{id}/tables/{invalid_id}/qr returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{self.restaurant_id}/tables/non-existent-id/qr",
            headers=self.headers
        )
        
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
