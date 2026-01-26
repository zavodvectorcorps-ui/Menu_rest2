"""
Backend API Tests for Restaurant Dashboard
Tests: Menu Sections, Call Types, Public Menu, Categories, Settings
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestMenuSections:
    """Menu Sections CRUD tests - Еда, Напитки, Кальяны"""
    
    def test_get_menu_sections(self):
        """Test GET /api/menu-sections returns sections"""
        response = requests.get(f"{BASE_URL}/api/menu-sections")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3  # At least food, drinks, hookah
        
        # Verify section structure
        section_names = [s['name'] for s in data]
        assert 'Еда' in section_names
        assert 'Напитки' in section_names
        assert 'Кальяны' in section_names
        
        # Verify section fields
        for section in data:
            assert 'id' in section
            assert 'name' in section
            assert 'sort_order' in section
            assert 'is_active' in section
    
    def test_create_menu_section(self):
        """Test POST /api/menu-sections creates new section"""
        test_name = f"TEST_Section_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": test_name,
            "sort_order": 99,
            "is_active": True
        }
        
        response = requests.post(f"{BASE_URL}/api/menu-sections", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data['name'] == test_name
        assert data['sort_order'] == 99
        assert data['is_active'] == True
        assert 'id' in data
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/menu-sections/{data['id']}")
    
    def test_update_menu_section(self):
        """Test PUT /api/menu-sections/{id} updates section"""
        # Create test section
        test_name = f"TEST_Update_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(f"{BASE_URL}/api/menu-sections", json={
            "name": test_name,
            "sort_order": 50,
            "is_active": True
        })
        section_id = create_response.json()['id']
        
        # Update section
        updated_name = f"TEST_Updated_{uuid.uuid4().hex[:8]}"
        update_response = requests.put(f"{BASE_URL}/api/menu-sections/{section_id}", json={
            "name": updated_name,
            "sort_order": 51,
            "is_active": False
        })
        assert update_response.status_code == 200
        
        data = update_response.json()
        assert data['name'] == updated_name
        assert data['sort_order'] == 51
        assert data['is_active'] == False
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/menu-sections/{section_id}")
    
    def test_delete_menu_section(self):
        """Test DELETE /api/menu-sections/{id} removes section"""
        # Create test section
        test_name = f"TEST_Delete_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(f"{BASE_URL}/api/menu-sections", json={
            "name": test_name,
            "sort_order": 100,
            "is_active": True
        })
        section_id = create_response.json()['id']
        
        # Delete section
        delete_response = requests.delete(f"{BASE_URL}/api/menu-sections/{section_id}")
        assert delete_response.status_code == 200
        
        # Verify deletion
        get_response = requests.get(f"{BASE_URL}/api/menu-sections")
        section_ids = [s['id'] for s in get_response.json()]
        assert section_id not in section_ids


class TestCallTypes:
    """Call Types CRUD tests - Официант, Кальянный мастер, Счёт"""
    
    def test_get_call_types(self):
        """Test GET /api/call-types returns call types"""
        response = requests.get(f"{BASE_URL}/api/call-types")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3  # At least waiter, hookah master, bill
        
        # Verify call type names
        call_names = [ct['name'] for ct in data]
        assert 'Вызов официанта' in call_names
        assert 'Вызов кальянного мастера' in call_names
        assert 'Попросить счёт' in call_names
        
        # Verify call type fields
        for ct in data:
            assert 'id' in ct
            assert 'name' in ct
            assert 'telegram_message' in ct
            assert 'sort_order' in ct
            assert 'is_active' in ct
    
    def test_create_call_type(self):
        """Test POST /api/call-types creates new call type"""
        test_name = f"TEST_CallType_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": test_name,
            "telegram_message": "🔔 Стол #{table} - Test call",
            "sort_order": 99,
            "is_active": True
        }
        
        response = requests.post(f"{BASE_URL}/api/call-types", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data['name'] == test_name
        assert data['telegram_message'] == "🔔 Стол #{table} - Test call"
        assert 'id' in data
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/call-types/{data['id']}")
    
    def test_update_call_type(self):
        """Test PUT /api/call-types/{id} updates call type"""
        # Create test call type
        test_name = f"TEST_CTUpdate_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(f"{BASE_URL}/api/call-types", json={
            "name": test_name,
            "telegram_message": "Original message",
            "sort_order": 50,
            "is_active": True
        })
        ct_id = create_response.json()['id']
        
        # Update call type
        updated_name = f"TEST_CTUpdated_{uuid.uuid4().hex[:8]}"
        update_response = requests.put(f"{BASE_URL}/api/call-types/{ct_id}", json={
            "name": updated_name,
            "telegram_message": "Updated message",
            "sort_order": 51,
            "is_active": False
        })
        assert update_response.status_code == 200
        
        data = update_response.json()
        assert data['name'] == updated_name
        assert data['telegram_message'] == "Updated message"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/call-types/{ct_id}")
    
    def test_delete_call_type(self):
        """Test DELETE /api/call-types/{id} removes call type"""
        # Create test call type
        test_name = f"TEST_CTDelete_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(f"{BASE_URL}/api/call-types", json={
            "name": test_name,
            "telegram_message": "To be deleted",
            "sort_order": 100,
            "is_active": True
        })
        ct_id = create_response.json()['id']
        
        # Delete call type
        delete_response = requests.delete(f"{BASE_URL}/api/call-types/{ct_id}")
        assert delete_response.status_code == 200
        
        # Verify deletion
        get_response = requests.get(f"{BASE_URL}/api/call-types")
        ct_ids = [ct['id'] for ct in get_response.json()]
        assert ct_id not in ct_ids


class TestPublicMenu:
    """Public Menu endpoint tests - /api/public/menu/{table_code}"""
    
    def test_get_public_menu_valid_table(self):
        """Test GET /api/public/menu/{table_code} returns full menu data"""
        response = requests.get(f"{BASE_URL}/api/public/menu/697DCAA5")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify all required fields
        assert 'table' in data
        assert 'restaurant' in data
        assert 'settings' in data
        assert 'sections' in data
        assert 'categories' in data
        assert 'items' in data
        assert 'call_types' in data
        
        # Verify sections
        sections = data['sections']
        assert len(sections) >= 3
        section_names = [s['name'] for s in sections]
        assert 'Еда' in section_names
        assert 'Напитки' in section_names
        assert 'Кальяны' in section_names
        
        # Verify call types
        call_types = data['call_types']
        assert len(call_types) >= 3
        
        # Verify currency is BYN
        assert data['settings']['currency'] == 'BYN'
    
    def test_get_public_menu_invalid_table(self):
        """Test GET /api/public/menu/{invalid_code} returns 404"""
        response = requests.get(f"{BASE_URL}/api/public/menu/INVALID123")
        assert response.status_code == 404
    
    def test_public_menu_categories_have_section_id(self):
        """Test that categories in public menu have section_id"""
        response = requests.get(f"{BASE_URL}/api/public/menu/697DCAA5")
        assert response.status_code == 200
        
        data = response.json()
        categories = data['categories']
        
        # Verify categories have section_id
        for cat in categories:
            assert 'section_id' in cat
            # section_id should be one of: food, drinks, hookah
            assert cat['section_id'] in ['food', 'drinks', 'hookah', None]


class TestCategories:
    """Categories CRUD tests with section_id"""
    
    def test_get_categories(self):
        """Test GET /api/categories returns categories"""
        response = requests.get(f"{BASE_URL}/api/categories")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        # Verify category structure
        for cat in data:
            assert 'id' in cat
            assert 'name' in cat
            assert 'section_id' in cat
            assert 'sort_order' in cat
            assert 'is_active' in cat
    
    def test_create_category_with_section(self):
        """Test POST /api/categories creates category with section_id"""
        test_name = f"TEST_Category_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": test_name,
            "section_id": "food",  # Assign to Еда section
            "sort_order": 99,
            "is_active": True
        }
        
        response = requests.post(f"{BASE_URL}/api/categories", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data['name'] == test_name
        assert data['section_id'] == "food"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/categories/{data['id']}")
    
    def test_update_category_section(self):
        """Test PUT /api/categories/{id} can change section_id"""
        # Create test category
        test_name = f"TEST_CatUpdate_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(f"{BASE_URL}/api/categories", json={
            "name": test_name,
            "section_id": "food",
            "sort_order": 50,
            "is_active": True
        })
        cat_id = create_response.json()['id']
        
        # Update category to different section
        update_response = requests.put(f"{BASE_URL}/api/categories/{cat_id}", json={
            "name": test_name,
            "section_id": "drinks",  # Change to Напитки
            "sort_order": 50,
            "is_active": True
        })
        assert update_response.status_code == 200
        
        data = update_response.json()
        assert data['section_id'] == "drinks"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/categories/{cat_id}")


class TestSettings:
    """Settings tests - currency, telegram integration"""
    
    def test_get_settings(self):
        """Test GET /api/settings returns settings"""
        response = requests.get(f"{BASE_URL}/api/settings")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify required fields
        assert 'currency' in data
        assert data['currency'] == 'BYN'
        assert 'telegram_bot_token' in data
        assert 'telegram_chat_id' in data
        assert 'online_menu_enabled' in data
        assert 'staff_call_enabled' in data
    
    def test_update_telegram_settings(self):
        """Test PUT /api/settings can update telegram settings"""
        # Get current settings
        get_response = requests.get(f"{BASE_URL}/api/settings")
        original_settings = get_response.json()
        
        # Update telegram settings
        test_token = "TEST_TOKEN_123"
        test_chat_id = "-1001234567890"
        
        update_response = requests.put(f"{BASE_URL}/api/settings", json={
            "telegram_bot_token": test_token,
            "telegram_chat_id": test_chat_id
        })
        assert update_response.status_code == 200
        
        data = update_response.json()
        assert data['telegram_bot_token'] == test_token
        assert data['telegram_chat_id'] == test_chat_id
        
        # Restore original settings
        requests.put(f"{BASE_URL}/api/settings", json={
            "telegram_bot_token": original_settings.get('telegram_bot_token', ''),
            "telegram_chat_id": original_settings.get('telegram_chat_id', '')
        })


class TestStaffCalls:
    """Staff calls tests with call_type_id"""
    
    def test_create_staff_call_with_type(self):
        """Test POST /api/staff-calls creates call with call_type_id"""
        # Get call types
        ct_response = requests.get(f"{BASE_URL}/api/call-types")
        call_types = ct_response.json()
        waiter_ct = next((ct for ct in call_types if 'официант' in ct['name'].lower()), None)
        
        if waiter_ct:
            payload = {
                "table_code": "697DCAA5",
                "call_type_id": waiter_ct['id']
            }
            
            response = requests.post(f"{BASE_URL}/api/staff-calls", json=payload)
            assert response.status_code == 200
            
            data = response.json()
            assert data['call_type_id'] == waiter_ct['id']
            assert data['call_type_name'] == waiter_ct['name']
    
    def test_get_staff_calls(self):
        """Test GET /api/staff-calls returns calls"""
        response = requests.get(f"{BASE_URL}/api/staff-calls")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)


class TestMenuItems:
    """Menu items tests including banners"""
    
    def test_get_menu_items(self):
        """Test GET /api/menu-items returns items"""
        response = requests.get(f"{BASE_URL}/api/menu-items")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
    
    def test_create_banner_item(self):
        """Test POST /api/menu-items can create banner (no price)"""
        # Get a category first
        cat_response = requests.get(f"{BASE_URL}/api/categories")
        categories = cat_response.json()
        if not categories:
            pytest.skip("No categories available")
        
        test_name = f"TEST_Banner_{uuid.uuid4().hex[:8]}"
        payload = {
            "category_id": categories[0]['id'],
            "name": test_name,
            "description": "Test banner description",
            "price": 0,  # Banners have no price
            "is_banner": True,
            "is_available": True
        }
        
        response = requests.post(f"{BASE_URL}/api/menu-items", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data['is_banner'] == True
        assert data['price'] == 0
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/menu-items/{data['id']}")


class TestImageUpload:
    """Image upload endpoint tests - POST /api/upload"""
    
    def test_upload_valid_image(self):
        """Test POST /api/upload with valid PNG image"""
        import io
        
        # Create a minimal valid PNG file
        png_header = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
        
        files = {'file': ('test.png', io.BytesIO(png_header), 'image/png')}
        response = requests.post(f"{BASE_URL}/api/upload", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert 'url' in data
        assert 'filename' in data
        assert data['url'].startswith('/uploads/')
        assert data['filename'].endswith('.png')
    
    def test_upload_invalid_file_type(self):
        """Test POST /api/upload rejects non-image files"""
        import io
        
        files = {'file': ('test.txt', io.BytesIO(b'test content'), 'text/plain')}
        response = requests.post(f"{BASE_URL}/api/upload", files=files)
        
        assert response.status_code == 400
        data = response.json()
        assert 'detail' in data
        assert 'формат' in data['detail'].lower() or 'разрешены' in data['detail'].lower()
    
    def test_upload_file_too_large(self):
        """Test POST /api/upload rejects files over 5MB"""
        import io
        
        # Create a 6MB file
        large_content = b'\x89PNG\r\n\x1a\n' + (b'\x00' * (6 * 1024 * 1024))
        files = {'file': ('large.png', io.BytesIO(large_content), 'image/png')}
        response = requests.post(f"{BASE_URL}/api/upload", files=files)
        
        assert response.status_code == 400
        data = response.json()
        assert 'detail' in data
        assert '5MB' in data['detail'] or 'большой' in data['detail'].lower()
    
    def test_upload_jpeg_image(self):
        """Test POST /api/upload accepts JPEG images"""
        import io
        
        # Minimal JPEG header
        jpeg_header = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9telegrambot_token=telegrambot_token=telegrambot_token=\xff\xd9'
        
        files = {'file': ('test.jpg', io.BytesIO(jpeg_header), 'image/jpeg')}
        response = requests.post(f"{BASE_URL}/api/upload", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert 'url' in data
        assert data['filename'].endswith('.jpg')


class TestQRCode:
    """QR code generation endpoint tests - GET /api/tables/{id}/qr"""
    
    TABLE_ID = "827c810f-6da7-4d0b-9cbb-833bf4490d34"
    TABLE_CODE = "697DCAA5"
    
    def test_get_qr_code_valid_table(self):
        """Test GET /api/tables/{id}/qr returns QR code data"""
        response = requests.get(
            f"{BASE_URL}/api/tables/{self.TABLE_ID}/qr",
            params={"base_url": BASE_URL}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert 'table_id' in data
        assert 'table_number' in data
        assert 'table_code' in data
        assert 'menu_url' in data
        assert 'qr_base64' in data
        
        # Verify values
        assert data['table_id'] == self.TABLE_ID
        assert data['table_code'] == self.TABLE_CODE
        assert data['table_number'] == 1
        
        # Verify QR code is base64 PNG
        assert data['qr_base64'].startswith('data:image/png;base64,')
        
        # Verify menu URL is correct
        assert f"/menu/{self.TABLE_CODE}" in data['menu_url']
    
    def test_get_qr_code_invalid_table(self):
        """Test GET /api/tables/{invalid_id}/qr returns 404"""
        response = requests.get(f"{BASE_URL}/api/tables/non-existent-id/qr")
        
        assert response.status_code == 404
        data = response.json()
        assert 'detail' in data
        assert 'not found' in data['detail'].lower()
    
    def test_qr_code_menu_url_format(self):
        """Test QR code contains correct menu URL format"""
        response = requests.get(
            f"{BASE_URL}/api/tables/{self.TABLE_ID}/qr",
            params={"base_url": "https://example.com"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Menu URL should be base_url + /menu/ + table_code
        expected_url = f"https://example.com/menu/{self.TABLE_CODE}"
        assert data['menu_url'] == expected_url
    
    def test_qr_code_download_endpoint(self):
        """Test GET /api/tables/{id}/qr/download returns PNG file"""
        response = requests.get(
            f"{BASE_URL}/api/tables/{self.TABLE_ID}/qr/download",
            params={"base_url": BASE_URL}
        )
        
        assert response.status_code == 200
        assert response.headers.get('content-type') == 'image/png'
        
        # Verify it's a valid PNG (starts with PNG signature)
        assert response.content[:8] == b'\x89PNG\r\n\x1a\n'
    
    def test_qr_code_download_invalid_table(self):
        """Test GET /api/tables/{invalid_id}/qr/download returns 404"""
        response = requests.get(f"{BASE_URL}/api/tables/non-existent-id/qr/download")
        
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
