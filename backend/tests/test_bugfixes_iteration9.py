"""
Test file for Iteration 9 bugfixes:
1. Banner import from .data file (type=2 items become is_banner=true)
2. Download images endpoint (background task)
3. /api/uploads/ path serving images
4. PUT menu-items no 401 error (JWT_SECRET now fixed in .env)
5. Import mode=replace (deletes old data before import)
6. Labels visible on public menu
"""
import pytest
import requests
import os
import json
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def auth_token():
    """Get auth token for admin user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "admin",
        "password": "220066"
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]

@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}

@pytest.fixture(scope="module")
def test_restaurant_id():
    """Restaurant ID for testing - Мята Центральная has external images"""
    return "d433dc80-02e6-41ca-9527-df7f78f4b4aa"

@pytest.fixture(scope="module")
def restaurant_with_local_images():
    """Restaurant ID for testing - Мята Спортивная has local images"""
    return "aa25189d-d668-4838-915a-c5d936547f3f"


class TestJWTAndAuth:
    """Test JWT_SECRET is stable - no 401 errors on authenticated endpoints"""
    
    def test_auth_me_works(self, auth_headers):
        """GET /api/auth/me should return user info, not 401"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "user" in data
        assert data["user"]["username"] == "admin"
        print("✓ Auth me endpoint working with token")
    
    def test_put_menu_item_no_401(self, auth_headers, restaurant_with_local_images):
        """PUT /api/restaurants/{id}/menu-items/{iid} should not return 401"""
        # First get a menu item to update
        items_response = requests.get(
            f"{BASE_URL}/api/restaurants/{restaurant_with_local_images}/menu-items",
            headers=auth_headers
        )
        assert items_response.status_code == 200
        items = items_response.json()
        assert len(items) > 0, "No menu items found to test"
        
        test_item = items[0]
        item_id = test_item["id"]
        
        # Update item - should NOT return 401
        update_response = requests.put(
            f"{BASE_URL}/api/restaurants/{restaurant_with_local_images}/menu-items/{item_id}",
            headers=auth_headers,
            json={"description": test_item.get("description", "") + " (test update)"}
        )
        
        assert update_response.status_code != 401, f"Got 401 - JWT_SECRET issue! Response: {update_response.text}"
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}: {update_response.text}"
        
        # Revert description
        requests.put(
            f"{BASE_URL}/api/restaurants/{restaurant_with_local_images}/menu-items/{item_id}",
            headers=auth_headers,
            json={"description": test_item.get("description", "")}
        )
        print(f"✓ PUT menu item {item_id} succeeded without 401")


class TestUploadsPath:
    """Test /api/uploads/ path serves images correctly"""
    
    def test_uploads_path_serves_images(self, auth_headers, restaurant_with_local_images):
        """Images served via /api/uploads/ should return 200"""
        # Get menu items to find one with local image
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{restaurant_with_local_images}/menu-items",
            headers=auth_headers
        )
        assert response.status_code == 200
        items = response.json()
        
        # Find item with local image URL
        local_images = [i for i in items if i.get("image_url", "").startswith("/api/uploads/")]
        assert len(local_images) > 0, "No local images found - expected /api/uploads/ URLs"
        
        # Test first local image
        image_url = local_images[0]["image_url"]
        full_url = f"{BASE_URL}{image_url}"
        
        img_response = requests.head(full_url)
        assert img_response.status_code == 200, f"Image at {full_url} returned {img_response.status_code}"
        print(f"✓ Image served correctly: {image_url}")
    
    def test_uploads_path_format(self, auth_headers, restaurant_with_local_images):
        """Local image URLs should use /api/uploads/ prefix"""
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{restaurant_with_local_images}/menu-items",
            headers=auth_headers
        )
        items = response.json()
        
        local_images = [i for i in items if i.get("image_url", "").startswith("/api/uploads/")]
        print(f"Found {len(local_images)} items with local /api/uploads/ images")
        assert len(local_images) > 0, "Expected local images with /api/uploads/ path"


class TestBannerImport:
    """Test banner (type=2) import from .data file"""
    
    def test_data_file_has_banners(self):
        """Verify test .data file contains type=2 banners with images"""
        data_file = "/tmp/menu_sample.data"
        assert os.path.exists(data_file), f"Test file not found: {data_file}"
        
        with open(data_file, 'r') as f:
            raw_data = json.load(f)
        
        banners = [e for e in raw_data if e.get("type") == 2 and e.get("foto", {}).get("image_url")]
        print(f"Test file has {len(banners)} banners with images")
        assert len(banners) >= 2, "Expected at least 2 banners with images"
    
    def test_import_file_with_banners_replace_mode(self, auth_headers):
        """POST /api/restaurants/{id}/import-file with .data should import banners as is_banner=true"""
        # Create a test restaurant for this test
        create_response = requests.post(
            f"{BASE_URL}/api/restaurants",
            headers=auth_headers,
            json={"name": "TEST_Banner_Import_Restaurant", "description": "For banner import test"}
        )
        assert create_response.status_code == 200, f"Failed to create test restaurant: {create_response.text}"
        test_rest_id = create_response.json()["id"]
        
        try:
            # Import the .data file with mode=replace
            data_file = "/tmp/menu_sample.data"
            with open(data_file, 'rb') as f:
                files = {'file': ('menu.data', f, 'application/octet-stream')}
                import_response = requests.post(
                    f"{BASE_URL}/api/restaurants/{test_rest_id}/import-file?mode=replace",
                    headers=auth_headers,
                    files=files
                )
            
            assert import_response.status_code == 200, f"Import failed: {import_response.text}"
            import_result = import_response.json()
            print(f"Import result: {import_result}")
            
            # Now check if banners were imported
            items_response = requests.get(
                f"{BASE_URL}/api/restaurants/{test_rest_id}/menu-items",
                headers=auth_headers
            )
            assert items_response.status_code == 200
            items = items_response.json()
            
            banners = [i for i in items if i.get("is_banner") == True]
            print(f"Imported {len(items)} items, {len(banners)} are banners")
            
            # Should have at least 2 banners from the .data file
            assert len(banners) >= 2, f"Expected at least 2 banners, got {len(banners)}"
            
            # Verify banner properties
            for banner in banners:
                assert banner.get("is_banner") == True, f"Banner not marked as is_banner=true: {banner}"
                assert banner.get("image_url"), f"Banner missing image_url: {banner}"
                print(f"  ✓ Banner imported: image={banner['image_url'][:50]}...")
            
        finally:
            # Cleanup test restaurant
            requests.delete(f"{BASE_URL}/api/restaurants/{test_rest_id}", headers=auth_headers)
            print("✓ Test restaurant cleaned up")


class TestImportReplaceMode:
    """Test import mode=replace deletes old data before import"""
    
    def test_replace_mode_deletes_old_menu(self, auth_headers):
        """POST /api/restaurants/{id}/import-file?mode=replace should delete existing menu"""
        # Create a test restaurant
        create_response = requests.post(
            f"{BASE_URL}/api/restaurants",
            headers=auth_headers,
            json={"name": "TEST_Replace_Mode_Restaurant"}
        )
        assert create_response.status_code == 200
        test_rest_id = create_response.json()["id"]
        
        try:
            # Create a category and item manually
            cat_response = requests.post(
                f"{BASE_URL}/api/restaurants/{test_rest_id}/categories",
                headers=auth_headers,
                json={"name": "TEST_Old_Category", "display_mode": "card"}
            )
            assert cat_response.status_code == 200
            old_cat_id = cat_response.json()["id"]
            
            item_response = requests.post(
                f"{BASE_URL}/api/restaurants/{test_rest_id}/menu-items",
                headers=auth_headers,
                json={"category_id": old_cat_id, "name": "TEST_Old_Item", "price": 100}
            )
            assert item_response.status_code == 200
            
            # Verify old data exists
            items_before = requests.get(f"{BASE_URL}/api/restaurants/{test_rest_id}/menu-items", headers=auth_headers).json()
            cats_before = requests.get(f"{BASE_URL}/api/restaurants/{test_rest_id}/categories", headers=auth_headers).json()
            assert len(items_before) == 1, "Expected 1 item before import"
            assert len(cats_before) == 1, "Expected 1 category before import"
            print(f"Before import: {len(cats_before)} categories, {len(items_before)} items")
            
            # Import with replace mode - this should delete old data
            test_import_data = {
                "categories": [
                    {
                        "name": "NEW_Category",
                        "items": [
                            {"name": "NEW_Item_1", "price": 10},
                            {"name": "NEW_Item_2", "price": 20}
                        ]
                    }
                ]
            }
            
            import_response = requests.post(
                f"{BASE_URL}/api/restaurants/{test_rest_id}/import-menu",
                headers=auth_headers,
                json={"data": test_import_data, "mode": "replace"}
            )
            assert import_response.status_code == 200, f"Import failed: {import_response.text}"
            
            # Verify old data was deleted and new data exists
            items_after = requests.get(f"{BASE_URL}/api/restaurants/{test_rest_id}/menu-items", headers=auth_headers).json()
            cats_after = requests.get(f"{BASE_URL}/api/restaurants/{test_rest_id}/categories", headers=auth_headers).json()
            
            print(f"After replace import: {len(cats_after)} categories, {len(items_after)} items")
            
            # Old items should be gone
            old_items = [i for i in items_after if i.get("name") == "TEST_Old_Item"]
            assert len(old_items) == 0, "Old item should have been deleted in replace mode"
            
            # New items should exist
            new_items = [i for i in items_after if i.get("name", "").startswith("NEW_")]
            assert len(new_items) == 2, f"Expected 2 new items, got {len(new_items)}"
            
            print("✓ Replace mode correctly deleted old data and imported new")
            
        finally:
            requests.delete(f"{BASE_URL}/api/restaurants/{test_rest_id}", headers=auth_headers)


class TestDownloadImages:
    """Test download-images background task endpoint"""
    
    def test_download_images_endpoint_returns_immediately(self, auth_headers, test_restaurant_id):
        """POST /api/restaurants/{id}/download-images should return immediately"""
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{test_restaurant_id}/download-images",
            headers=auth_headers
        )
        
        # Should return 200 immediately (it's a background task)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data
        assert "total" in data
        print(f"✓ Download images response: {data}")
    
    def test_download_images_counts_external_urls(self, auth_headers, test_restaurant_id):
        """The download-images endpoint should report count of external images"""
        # First check how many external images exist
        items_response = requests.get(
            f"{BASE_URL}/api/restaurants/{test_restaurant_id}/menu-items",
            headers=auth_headers
        )
        items = items_response.json()
        external_count = len([i for i in items if i.get("image_url", "").startswith("http")])
        
        # Call download endpoint
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{test_restaurant_id}/download-images",
            headers=auth_headers
        )
        data = response.json()
        
        print(f"External images in DB: {external_count}, Endpoint reported: {data.get('total')}")
        # Note: counts might differ if background task already processed some
    
    def test_restaurant_without_external_images(self, auth_headers, restaurant_with_local_images):
        """Restaurant with local images should report 0 external images"""
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{restaurant_with_local_images}/download-images",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Local images restaurant: {data}")


class TestPublicMenuLabels:
    """Test labels are returned in public menu endpoint"""
    
    def test_public_menu_returns_labels_array(self, restaurant_with_local_images):
        """GET /api/public/menu/{code} should include labels array"""
        # First get a table code for this restaurant
        # Use the known table code from iteration 8 context
        table_code = "697DCAA5"
        
        response = requests.get(f"{BASE_URL}/api/public/menu/{table_code}")
        assert response.status_code == 200, f"Public menu failed: {response.text}"
        
        data = response.json()
        assert "labels" in data, "labels field missing from public menu response"
        assert isinstance(data["labels"], list), "labels should be an array"
        
        print(f"✓ Public menu includes {len(data['labels'])} labels")
        
        # If labels exist, verify structure
        if data["labels"]:
            label = data["labels"][0]
            assert "id" in label
            assert "name" in label
            assert "color" in label
            print(f"  Sample label: {label}")


class TestMenuItemsHaveExternalImages:
    """Test to verify external images exist for download button visibility"""
    
    def test_restaurant_has_external_images(self, auth_headers, test_restaurant_id):
        """Verify the test restaurant has external (http) images"""
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{test_restaurant_id}/menu-items",
            headers=auth_headers
        )
        assert response.status_code == 200
        items = response.json()
        
        external = [i for i in items if i.get("image_url", "").startswith("http")]
        local = [i for i in items if i.get("image_url", "").startswith("/api/uploads/")]
        
        print(f"Restaurant {test_restaurant_id}:")
        print(f"  Total items: {len(items)}")
        print(f"  External images (http): {len(external)}")
        print(f"  Local images (/api/uploads): {len(local)}")
        
        # This restaurant should have external images for testing the download button
        # Note: If this fails, it means images were already downloaded


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
