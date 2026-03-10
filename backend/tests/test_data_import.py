"""
Test cases for .data file import feature (LunchPad format)
Tests the following:
1. POST /api/restaurants/{id}/import-file with .data file → parses LunchPad format
2. POST /api/restaurants/{id}/import-file with .json file → imports standard JSON format
3. POST /api/restaurants/{id}/import-file rejects non .data/.json files
4. POST /api/restaurants/{id}/import-file requires auth
5. Verify HTML tags stripped from imported item names/descriptions
6. Verify prices parsed correctly from LunchPad format
7. Verify image_url imported from foto.image_url field
8. Verify display mode mapping: grid→card, list/empty→compact
"""

import pytest
import requests
import os
import json
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test Restaurant: Мята Спортивная
RESTAURANT_ID = "aa25189d-d668-4838-915a-c5d936547f3f"
SAMPLE_DATA_FILE = "/tmp/menu_sample.data"

# Sample LunchPad .data content (small subset for testing)
SAMPLE_LUNCHPAD_DATA = [
    {
        "type": 0,  # Category
        "name": "<p style=\"margin: 0;\">TEST_Import_Category_Grid</p>",
        "display": "grid",
        "in_stop_list": False,
        "items": [
            {
                "type": 4,  # Item
                "name": "TEST_Import_Item_1",
                "description": "<p style=\"margin: 0;\">Description with <b>HTML</b> tags</p>",
                "prices": [{"measure": "200гр", "price": "15.5"}],
                "foto": {"image_url": "https://example.com/image1.jpg", "image_url_thumb": "https://example.com/image1_thumb.jpg"},
                "in_stop_list": False
            },
            {
                "type": 4,
                "name": "TEST_Import_Item_2",
                "description": "",
                "prices": [{"measure": "300гр", "price": 25}],
                "foto": None,
                "in_stop_list": True  # Should set is_available=False
            }
        ]
    },
    {
        "type": 0,
        "name": "TEST_Import_Category_List",
        "display": "list",  # Should map to compact
        "in_stop_list": False,
        "items": [
            {
                "type": 4,
                "name": "TEST_Import_Item_3",
                "description": "<span>Test description</span>",
                "prices": [{"measure": "50мл", "price": "5"}],
                "foto": {"image_url": "https://example.com/image3.jpg"},
                "in_stop_list": False
            }
        ]
    },
    {
        "type": 2,  # Should be skipped (not a category)
        "name": "TEST_Banner_Should_Be_Skipped",
        "items": []
    }
]

# Standard JSON format for comparison
SAMPLE_JSON_DATA = {
    "categories": [
        {
            "name": "TEST_JSON_Import_Category",
            "display_mode": "card",
            "items": [
                {
                    "name": "TEST_JSON_Import_Item",
                    "description": "JSON item description",
                    "price": 12.5,
                    "weight": "150гр",
                    "image_url": "https://example.com/json_image.jpg",
                    "is_available": True
                }
            ]
        }
    ]
}


class TestDataImportAuth:
    """Test authentication requirements for import-file endpoint"""
    
    def test_import_file_requires_auth(self):
        """POST /api/restaurants/{id}/import-file without auth returns 401"""
        files = {'file': ('test.data', io.BytesIO(b'[]'), 'application/octet-stream')}
        response = requests.post(f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/import-file", files=files)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✓ Import file endpoint requires authentication")


class TestDataImportFormats:
    """Test file format validation"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "220066"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["access_token"]
    
    def test_import_rejects_non_data_json_files(self, auth_token):
        """POST /api/restaurants/{id}/import-file rejects non .data/.json files"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Test .txt file
        files = {'file': ('test.txt', io.BytesIO(b'{"test": 1}'), 'text/plain')}
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/import-file",
            files=files,
            headers=headers
        )
        assert response.status_code == 400, f"Expected 400 for .txt, got {response.status_code}"
        assert "формат" in response.json().get("detail", "").lower() or "data" in response.json().get("detail", "").lower()
        print("✓ Import rejects .txt files")
        
        # Test .csv file
        files = {'file': ('test.csv', io.BytesIO(b'name,price\nitem1,10'), 'text/csv')}
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/import-file",
            files=files,
            headers=headers
        )
        assert response.status_code == 400, f"Expected 400 for .csv, got {response.status_code}"
        print("✓ Import rejects .csv files")
        
        # Test .xml file
        files = {'file': ('test.xml', io.BytesIO(b'<menu></menu>'), 'application/xml')}
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/import-file",
            files=files,
            headers=headers
        )
        assert response.status_code == 400, f"Expected 400 for .xml, got {response.status_code}"
        print("✓ Import rejects .xml files")
    
    def test_import_accepts_data_file(self, auth_token):
        """POST /api/restaurants/{id}/import-file accepts .data files"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        content = json.dumps(SAMPLE_LUNCHPAD_DATA).encode('utf-8')
        files = {'file': ('menu.data', io.BytesIO(content), 'application/octet-stream')}
        
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/import-file",
            files=files,
            headers=headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert "imported_categories" in result
        assert "imported_items" in result
        assert result["imported_categories"] >= 2  # At least 2 test categories
        print(f"✓ Import .data file accepted: {result['imported_categories']} categories, {result['imported_items']} items")
    
    def test_import_accepts_json_file(self, auth_token):
        """POST /api/restaurants/{id}/import-file accepts .json files"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        content = json.dumps(SAMPLE_JSON_DATA).encode('utf-8')
        files = {'file': ('menu.json', io.BytesIO(content), 'application/json')}
        
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/import-file",
            files=files,
            headers=headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert "imported_categories" in result
        assert "imported_items" in result
        print(f"✓ Import .json file accepted: {result['imported_categories']} categories, {result['imported_items']} items")


class TestLunchPadParsing:
    """Test LunchPad .data format parsing"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "220066"
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_html_tags_stripped_from_names(self, auth_headers):
        """Verify HTML tags stripped from imported item names/descriptions"""
        # Create test data with HTML
        test_data = [{
            "type": 0,
            "name": "<p style=\"margin: 0;\">TEST_HTML_Strip_Category</p>",
            "display": "grid",
            "in_stop_list": False,
            "items": [{
                "type": 4,
                "name": "<b>TEST_HTML_Strip_Item</b>",
                "description": "<p>Description <span>with</span> <strong>HTML</strong></p>",
                "prices": [{"measure": "", "price": "10"}],
                "foto": None,
                "in_stop_list": False
            }]
        }]
        
        content = json.dumps(test_data).encode('utf-8')
        files = {'file': ('test_html.data', io.BytesIO(content), 'application/octet-stream')}
        
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/import-file",
            files=files,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Import failed: {response.text}"
        
        # Verify category name has no HTML
        cats_response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/categories",
            headers=auth_headers
        )
        categories = cats_response.json()
        test_cat = next((c for c in categories if "TEST_HTML_Strip_Category" in c["name"]), None)
        
        if test_cat:
            assert "<p" not in test_cat["name"], f"HTML not stripped from category name: {test_cat['name']}"
            assert "margin" not in test_cat["name"], f"HTML style not stripped: {test_cat['name']}"
            print(f"✓ Category name HTML stripped: '{test_cat['name']}'")
            
            # Verify item description has no HTML
            items_response = requests.get(
                f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/menu-items",
                params={"category_id": test_cat["id"]},
                headers=auth_headers
            )
            items = items_response.json()
            test_item = next((i for i in items if "TEST_HTML_Strip_Item" in i["name"]), None)
            
            if test_item:
                assert "<p>" not in test_item.get("description", ""), f"HTML not stripped from description"
                assert "<span>" not in test_item.get("description", ""), f"HTML not stripped from description"
                print(f"✓ Item description HTML stripped: '{test_item.get('description', '')}'")
    
    def test_prices_parsed_correctly(self, auth_headers):
        """Verify prices parsed correctly from LunchPad format"""
        test_data = [{
            "type": 0,
            "name": "TEST_Price_Parse_Category",
            "display": "grid",
            "in_stop_list": False,
            "items": [
                {
                    "type": 4,
                    "name": "TEST_Price_String",
                    "description": "",
                    "prices": [{"measure": "200гр", "price": "15.5"}],  # String price
                    "foto": None,
                    "in_stop_list": False
                },
                {
                    "type": 4,
                    "name": "TEST_Price_Number",
                    "description": "",
                    "prices": [{"measure": "300гр", "price": 25}],  # Number price
                    "foto": None,
                    "in_stop_list": False
                },
                {
                    "type": 4,
                    "name": "TEST_Price_Null",
                    "description": "",
                    "prices": [{"measure": "", "price": None}],  # Null price
                    "foto": None,
                    "in_stop_list": False
                }
            ]
        }]
        
        content = json.dumps(test_data).encode('utf-8')
        files = {'file': ('test_prices.data', io.BytesIO(content), 'application/octet-stream')}
        
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/import-file",
            files=files,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Get items to verify prices
        cats_response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/categories",
            headers=auth_headers
        )
        categories = cats_response.json()
        test_cat = next((c for c in categories if c["name"] == "TEST_Price_Parse_Category"), None)
        
        if test_cat:
            items_response = requests.get(
                f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/menu-items",
                params={"category_id": test_cat["id"]},
                headers=auth_headers
            )
            items = items_response.json()
            
            for item in items:
                if item["name"] == "TEST_Price_String":
                    assert item["price"] == 15.5, f"String price not parsed: {item['price']}"
                    assert item["weight"] == "200гр", f"Weight not parsed: {item['weight']}"
                    print(f"✓ String price parsed correctly: {item['price']} ({item['weight']})")
                
                elif item["name"] == "TEST_Price_Number":
                    assert item["price"] == 25, f"Number price not parsed: {item['price']}"
                    print(f"✓ Number price parsed correctly: {item['price']}")
                
                elif item["name"] == "TEST_Price_Null":
                    assert item["price"] == 0, f"Null price should be 0: {item['price']}"
                    print(f"✓ Null price defaults to 0: {item['price']}")
    
    def test_image_url_from_foto_field(self, auth_headers):
        """Verify image_url imported from foto.image_url field"""
        test_image_url = "https://example.com/test_image_123.jpg"
        test_data = [{
            "type": 0,
            "name": "TEST_Image_URL_Category",
            "display": "grid",
            "in_stop_list": False,
            "items": [{
                "type": 4,
                "name": "TEST_Image_URL_Item",
                "description": "",
                "prices": [{"measure": "", "price": "10"}],
                "foto": {"image_url": test_image_url, "image_url_thumb": "https://example.com/thumb.jpg"},
                "in_stop_list": False
            }]
        }]
        
        content = json.dumps(test_data).encode('utf-8')
        files = {'file': ('test_image.data', io.BytesIO(content), 'application/octet-stream')}
        
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/import-file",
            files=files,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Find and verify the item
        cats_response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/categories",
            headers=auth_headers
        )
        categories = cats_response.json()
        test_cat = next((c for c in categories if c["name"] == "TEST_Image_URL_Category"), None)
        
        if test_cat:
            items_response = requests.get(
                f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/menu-items",
                params={"category_id": test_cat["id"]},
                headers=auth_headers
            )
            items = items_response.json()
            test_item = next((i for i in items if i["name"] == "TEST_Image_URL_Item"), None)
            
            if test_item:
                assert test_item["image_url"] == test_image_url, f"Image URL not imported: {test_item['image_url']}"
                print(f"✓ Image URL imported correctly: {test_item['image_url']}")
    
    def test_display_mode_mapping(self, auth_headers):
        """Verify display mode mapping: grid→card, list/empty→compact"""
        test_data = [
            {
                "type": 0,
                "name": "TEST_Display_Grid_Category",
                "display": "grid",  # Should map to "card"
                "in_stop_list": False,
                "items": []
            },
            {
                "type": 0,
                "name": "TEST_Display_List_Category",
                "display": "list",  # Should map to "compact"
                "in_stop_list": False,
                "items": []
            },
            {
                "type": 0,
                "name": "TEST_Display_Empty_Category",
                "display": "",  # Should map to "compact"
                "in_stop_list": False,
                "items": []
            }
        ]
        
        content = json.dumps(test_data).encode('utf-8')
        files = {'file': ('test_display.data', io.BytesIO(content), 'application/octet-stream')}
        
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/import-file",
            files=files,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Verify display modes
        cats_response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/categories",
            headers=auth_headers
        )
        categories = cats_response.json()
        
        grid_cat = next((c for c in categories if c["name"] == "TEST_Display_Grid_Category"), None)
        list_cat = next((c for c in categories if c["name"] == "TEST_Display_List_Category"), None)
        empty_cat = next((c for c in categories if c["name"] == "TEST_Display_Empty_Category"), None)
        
        if grid_cat:
            assert grid_cat["display_mode"] == "card", f"Grid should map to card: {grid_cat['display_mode']}"
            print(f"✓ grid→card mapping correct: {grid_cat['display_mode']}")
        
        if list_cat:
            assert list_cat["display_mode"] == "compact", f"List should map to compact: {list_cat['display_mode']}"
            print(f"✓ list→compact mapping correct: {list_cat['display_mode']}")
        
        if empty_cat:
            assert empty_cat["display_mode"] == "compact", f"Empty should map to compact: {empty_cat['display_mode']}"
            print(f"✓ empty→compact mapping correct: {empty_cat['display_mode']}")
    
    def test_in_stop_list_maps_to_is_available(self, auth_headers):
        """Verify in_stop_list→is_available mapping (inverted)"""
        test_data = [{
            "type": 0,
            "name": "TEST_Availability_Category",
            "display": "grid",
            "in_stop_list": False,
            "items": [
                {
                    "type": 4,
                    "name": "TEST_Available_Item",
                    "description": "",
                    "prices": [{"measure": "", "price": "10"}],
                    "foto": None,
                    "in_stop_list": False  # is_available should be True
                },
                {
                    "type": 4,
                    "name": "TEST_Unavailable_Item",
                    "description": "",
                    "prices": [{"measure": "", "price": "10"}],
                    "foto": None,
                    "in_stop_list": True  # is_available should be False
                }
            ]
        }]
        
        content = json.dumps(test_data).encode('utf-8')
        files = {'file': ('test_avail.data', io.BytesIO(content), 'application/octet-stream')}
        
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/import-file",
            files=files,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Verify availability
        cats_response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/categories",
            headers=auth_headers
        )
        categories = cats_response.json()
        test_cat = next((c for c in categories if c["name"] == "TEST_Availability_Category"), None)
        
        if test_cat:
            items_response = requests.get(
                f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/menu-items",
                params={"category_id": test_cat["id"]},
                headers=auth_headers
            )
            items = items_response.json()
            
            avail_item = next((i for i in items if i["name"] == "TEST_Available_Item"), None)
            unavail_item = next((i for i in items if i["name"] == "TEST_Unavailable_Item"), None)
            
            if avail_item:
                assert avail_item["is_available"] == True, f"in_stop_list=False should be available"
                print(f"✓ in_stop_list=False → is_available=True")
            
            if unavail_item:
                assert unavail_item["is_available"] == False, f"in_stop_list=True should be unavailable"
                print(f"✓ in_stop_list=True → is_available=False")


class TestRealDataImport:
    """Test importing the real sample .data file"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "220066"
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_import_real_sample_data_file(self, auth_token):
        """Test importing the actual /tmp/menu_sample.data file"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        if not os.path.exists(SAMPLE_DATA_FILE):
            pytest.skip(f"Sample file not found: {SAMPLE_DATA_FILE}")
        
        with open(SAMPLE_DATA_FILE, 'rb') as f:
            files = {'file': ('menu_sample.data', f, 'application/octet-stream')}
            response = requests.post(
                f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/import-file",
                files=files,
                headers=headers
            )
        
        assert response.status_code == 200, f"Import failed: {response.text}"
        
        result = response.json()
        assert "imported_categories" in result
        assert "imported_items" in result
        
        # The sample file has 28 categories and 178 items (according to context)
        print(f"✓ Real sample file imported: {result['imported_categories']} categories, {result['imported_items']} items")


class TestCleanup:
    """Cleanup test data created during testing"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "220066"
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_cleanup_test_data(self, auth_token):
        """Clean up TEST_ prefixed categories and items"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Get all categories
        cats_response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/categories",
            headers=headers
        )
        categories = cats_response.json()
        
        # Delete TEST_ prefixed categories
        deleted_cats = 0
        for cat in categories:
            if cat["name"].startswith("TEST_"):
                del_response = requests.delete(
                    f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/categories/{cat['id']}",
                    headers=headers
                )
                if del_response.status_code == 200:
                    deleted_cats += 1
        
        print(f"✓ Cleaned up {deleted_cats} test categories")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
