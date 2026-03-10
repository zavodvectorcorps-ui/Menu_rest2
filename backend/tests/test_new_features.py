"""
Tests for new features in iteration_8:
1. Labels CRUD API
2. Label assignment to menu items (label_ids)
3. Import menu with mode=replace/append
4. Public menu returns labels
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
RESTAURANT_ID = "aa25189d-d668-4838-915a-c5d936547f3f"  # Мята Спортивная
RESTAURANT_ID_2 = "d433dc80-02e6-41ca-9527-df7f78f4b4aa"  # Мята Центральная


@pytest.fixture(scope="module")
def auth_headers():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "admin",
        "password": "220066"
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestLabelsAPI:
    """Tests for labels CRUD endpoints"""
    
    created_label_ids = []
    
    def test_get_labels(self, auth_headers):
        """GET /api/restaurants/{id}/labels - list labels"""
        response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/labels",
            headers=auth_headers
        )
        assert response.status_code == 200
        labels = response.json()
        assert isinstance(labels, list)
        print(f"SUCCESS: GET labels returned {len(labels)} labels")
        # Store existing labels for reference
        for label in labels:
            print(f"  - Label: {label.get('name')} (color: {label.get('color')}, id: {label.get('id')})")
    
    def test_create_label(self, auth_headers):
        """POST /api/restaurants/{id}/labels - create label"""
        test_label = {
            "name": f"TEST_Label_{uuid.uuid4().hex[:6]}",
            "color": "#ff5733"
        }
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/labels",
            headers=auth_headers,
            json=test_label
        )
        assert response.status_code == 200
        label = response.json()
        assert label["name"] == test_label["name"]
        assert label["color"] == test_label["color"]
        assert "id" in label
        self.__class__.created_label_ids.append(label["id"])
        print(f"SUCCESS: Created label {label['name']} with id {label['id']}")
        return label
    
    def test_update_label(self, auth_headers):
        """PUT /api/restaurants/{id}/labels/{lid} - update label"""
        # First create a label to update
        create_response = requests.post(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/labels",
            headers=auth_headers,
            json={"name": f"TEST_Update_{uuid.uuid4().hex[:6]}", "color": "#123456"}
        )
        assert create_response.status_code == 200
        label_id = create_response.json()["id"]
        self.__class__.created_label_ids.append(label_id)
        
        # Update the label
        updated_data = {"name": "TEST_Updated_Name", "color": "#abcdef"}
        response = requests.put(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/labels/{label_id}",
            headers=auth_headers,
            json=updated_data
        )
        assert response.status_code == 200
        updated_label = response.json()
        assert updated_label["name"] == "TEST_Updated_Name"
        assert updated_label["color"] == "#abcdef"
        print(f"SUCCESS: Updated label to name={updated_label['name']}, color={updated_label['color']}")
    
    def test_delete_label(self, auth_headers):
        """DELETE /api/restaurants/{id}/labels/{lid} - delete label"""
        # First create a label to delete
        create_response = requests.post(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/labels",
            headers=auth_headers,
            json={"name": f"TEST_Delete_{uuid.uuid4().hex[:6]}", "color": "#999999"}
        )
        assert create_response.status_code == 200
        label_id = create_response.json()["id"]
        
        # Delete the label
        response = requests.delete(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/labels/{label_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Verify it's deleted
        get_response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/labels",
            headers=auth_headers
        )
        labels = get_response.json()
        assert not any(l["id"] == label_id for l in labels)
        print(f"SUCCESS: Deleted label {label_id}")
    
    def test_delete_label_clears_from_items(self, auth_headers):
        """DELETE label should also remove label_id from menu items"""
        # Create a label
        label_response = requests.post(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/labels",
            headers=auth_headers,
            json={"name": f"TEST_ClearFromItems_{uuid.uuid4().hex[:6]}", "color": "#ff0000"}
        )
        assert label_response.status_code == 200
        label_id = label_response.json()["id"]
        
        # Get first category to create test item
        cats_response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/categories",
            headers=auth_headers
        )
        categories = cats_response.json()
        assert len(categories) > 0, "No categories found for testing"
        cat_id = categories[0]["id"]
        
        # Create item with this label
        item_response = requests.post(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/menu-items",
            headers=auth_headers,
            json={
                "category_id": cat_id,
                "name": f"TEST_ItemWithLabel_{uuid.uuid4().hex[:6]}",
                "price": 10.0,
                "label_ids": [label_id]
            }
        )
        assert item_response.status_code == 200
        item_id = item_response.json()["id"]
        
        # Verify item has label_ids
        get_item = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/menu-items",
            headers=auth_headers
        )
        items = get_item.json()
        test_item = next((i for i in items if i["id"] == item_id), None)
        assert test_item is not None
        assert label_id in test_item.get("label_ids", [])
        print(f"SUCCESS: Item {item_id} has label_id {label_id}")
        
        # Delete the label
        del_response = requests.delete(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/labels/{label_id}",
            headers=auth_headers
        )
        assert del_response.status_code == 200
        
        # Verify item no longer has that label_id
        get_items_after = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/menu-items",
            headers=auth_headers
        )
        items_after = get_items_after.json()
        test_item_after = next((i for i in items_after if i["id"] == item_id), None)
        assert test_item_after is not None
        assert label_id not in test_item_after.get("label_ids", [])
        print(f"SUCCESS: After deleting label, item {item_id} no longer has label_id {label_id}")
        
        # Cleanup test item
        requests.delete(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/menu-items/{item_id}",
            headers=auth_headers
        )


class TestMenuItemLabels:
    """Tests for label_ids in menu items"""
    
    created_item_ids = []
    
    def test_create_item_with_labels(self, auth_headers):
        """POST /api/restaurants/{id}/menu-items with label_ids"""
        # Get existing labels
        labels_response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/labels",
            headers=auth_headers
        )
        labels = labels_response.json()
        
        # Get first category
        cats_response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/categories",
            headers=auth_headers
        )
        categories = cats_response.json()
        assert len(categories) > 0
        cat_id = categories[0]["id"]
        
        # Create item with label_ids (use existing labels if available)
        label_ids = [l["id"] for l in labels[:2]] if labels else []
        item_data = {
            "category_id": cat_id,
            "name": f"TEST_ItemWithLabels_{uuid.uuid4().hex[:6]}",
            "price": 25.0,
            "label_ids": label_ids
        }
        
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/menu-items",
            headers=auth_headers,
            json=item_data
        )
        assert response.status_code == 200
        item = response.json()
        assert item["label_ids"] == label_ids
        self.__class__.created_item_ids.append(item["id"])
        print(f"SUCCESS: Created item with label_ids: {label_ids}")
        return item
    
    def test_update_item_labels(self, auth_headers):
        """PUT /api/restaurants/{id}/menu-items/{iid} with label_ids"""
        # Get existing labels
        labels_response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/labels",
            headers=auth_headers
        )
        labels = labels_response.json()
        
        # Get a category
        cats_response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/categories",
            headers=auth_headers
        )
        categories = cats_response.json()
        cat_id = categories[0]["id"]
        
        # Create item without labels
        create_response = requests.post(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/menu-items",
            headers=auth_headers,
            json={
                "category_id": cat_id,
                "name": f"TEST_UpdateLabels_{uuid.uuid4().hex[:6]}",
                "price": 15.0,
                "label_ids": []
            }
        )
        assert create_response.status_code == 200
        item_id = create_response.json()["id"]
        self.__class__.created_item_ids.append(item_id)
        
        # Update with labels
        new_label_ids = [l["id"] for l in labels[:2]] if labels else []
        update_response = requests.put(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/menu-items/{item_id}",
            headers=auth_headers,
            json={"label_ids": new_label_ids}
        )
        assert update_response.status_code == 200
        updated_item = update_response.json()
        assert updated_item["label_ids"] == new_label_ids
        print(f"SUCCESS: Updated item labels to: {new_label_ids}")


class TestImportModes:
    """Tests for import menu with mode=replace/append"""
    
    def test_import_with_append_mode(self, auth_headers):
        """POST /api/restaurants/{id}/import-menu with mode=append"""
        # Count existing categories before import
        cats_before = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/categories",
            headers=auth_headers
        ).json()
        count_before = len(cats_before)
        
        # Import with append mode
        import_data = {
            "data": {
                "categories": [
                    {
                        "name": f"TEST_AppendCat_{uuid.uuid4().hex[:6]}",
                        "items": [
                            {"name": f"TEST_AppendItem_{uuid.uuid4().hex[:6]}", "price": 5.0}
                        ]
                    }
                ]
            },
            "mode": "append"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/import-menu",
            headers=auth_headers,
            json=import_data
        )
        assert response.status_code == 200
        result = response.json()
        assert "imported_categories" in result
        assert result["imported_categories"] >= 1
        print(f"SUCCESS: Append import created {result['imported_categories']} categories, {result['imported_items']} items")
        
        # Verify categories count increased
        cats_after = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/categories",
            headers=auth_headers
        ).json()
        assert len(cats_after) >= count_before + 1
        print(f"SUCCESS: Categories count increased from {count_before} to {len(cats_after)}")
    
    def test_import_with_replace_mode(self, auth_headers):
        """POST /api/restaurants/{id}/import-menu with mode=replace"""
        # Use the second restaurant to avoid affecting test data
        # First, create some test data
        create_cat = requests.post(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID_2}/categories",
            headers=auth_headers,
            json={"name": f"TEST_BeforeReplace_{uuid.uuid4().hex[:6]}"}
        )
        
        # Count categories before
        cats_before = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID_2}/categories",
            headers=auth_headers
        ).json()
        
        # Import with replace mode - should delete all existing and create new
        import_data = {
            "data": {
                "categories": [
                    {
                        "name": f"TEST_ReplacedCat_{uuid.uuid4().hex[:6]}",
                        "items": [
                            {"name": f"TEST_ReplacedItem_{uuid.uuid4().hex[:6]}", "price": 10.0}
                        ]
                    }
                ]
            },
            "mode": "replace"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID_2}/import-menu",
            headers=auth_headers,
            json=import_data
        )
        assert response.status_code == 200
        result = response.json()
        print(f"SUCCESS: Replace import created {result['imported_categories']} categories, {result['imported_items']} items")
        
        # Verify old categories are gone
        cats_after = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID_2}/categories",
            headers=auth_headers
        ).json()
        
        # After replace, should only have the newly imported categories
        # Old TEST_BeforeReplace category should be gone
        old_cat_names = [c["name"] for c in cats_before if "TEST_BeforeReplace" in c["name"]]
        new_cat_names = [c["name"] for c in cats_after]
        for old_name in old_cat_names:
            assert old_name not in new_cat_names, f"Old category {old_name} should have been deleted"
        print(f"SUCCESS: Replace mode deleted old categories. New count: {len(cats_after)}")
    
    def test_import_file_with_mode_replace(self, auth_headers):
        """POST /api/restaurants/{id}/import-file?mode=replace"""
        # Create a temporary JSON file content
        import json
        file_content = json.dumps({
            "categories": [
                {
                    "name": f"TEST_FileReplace_{uuid.uuid4().hex[:6]}",
                    "items": [{"name": f"TEST_FileItem_{uuid.uuid4().hex[:6]}", "price": 7.0}]
                }
            ]
        })
        
        # Import file with mode=replace
        files = {"file": ("test.json", file_content, "application/json")}
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID_2}/import-file?mode=replace",
            headers=auth_headers,
            files=files
        )
        assert response.status_code == 200
        result = response.json()
        print(f"SUCCESS: File import with mode=replace created {result['imported_categories']} categories")
    
    def test_import_file_with_mode_append(self, auth_headers):
        """POST /api/restaurants/{id}/import-file?mode=append"""
        import json
        
        # Count before
        cats_before = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID_2}/categories",
            headers=auth_headers
        ).json()
        
        file_content = json.dumps({
            "categories": [
                {
                    "name": f"TEST_FileAppend_{uuid.uuid4().hex[:6]}",
                    "items": [{"name": f"TEST_FileAppendItem_{uuid.uuid4().hex[:6]}", "price": 8.0}]
                }
            ]
        })
        
        files = {"file": ("test.json", file_content, "application/json")}
        response = requests.post(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID_2}/import-file?mode=append",
            headers=auth_headers,
            files=files
        )
        assert response.status_code == 200
        result = response.json()
        
        # Verify count increased
        cats_after = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID_2}/categories",
            headers=auth_headers
        ).json()
        assert len(cats_after) >= len(cats_before) + 1
        print(f"SUCCESS: File import with mode=append added categories. Count: {len(cats_before)} -> {len(cats_after)}")


class TestPublicMenuLabels:
    """Tests for labels in public menu response"""
    
    def test_public_menu_returns_labels(self, auth_headers):
        """GET /api/public/menu/{code} - should return labels"""
        # Get a table code
        tables_response = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/tables",
            headers=auth_headers
        )
        tables = tables_response.json()
        
        if not tables:
            # Create a table if none exist
            create_table = requests.post(
                f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/tables",
                headers=auth_headers,
                json={"number": 999, "name": "Test Table"}
            )
            assert create_table.status_code == 200
            table_code = create_table.json()["code"]
        else:
            table_code = tables[0]["code"]
        
        # Get public menu (no auth needed)
        response = requests.get(f"{BASE_URL}/api/public/menu/{table_code}")
        assert response.status_code == 200
        data = response.json()
        
        # Verify labels are present in response
        assert "labels" in data, "Public menu response should include 'labels' field"
        labels = data["labels"]
        assert isinstance(labels, list)
        print(f"SUCCESS: Public menu returns {len(labels)} labels")
        
        # Verify label structure
        if labels:
            label = labels[0]
            assert "id" in label
            assert "name" in label
            assert "color" in label
            print(f"  - Sample label: {label['name']} ({label['color']})")
        
        # Verify items have label_ids field
        items = data.get("items", [])
        if items:
            item = items[0]
            assert "label_ids" in item or item.get("label_ids") == [], "Items should have label_ids field"
            print(f"SUCCESS: Items have label_ids field")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_data(self, auth_headers):
        """Delete all TEST_ prefixed data"""
        # Cleanup categories and items in restaurant 2
        cats = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID_2}/categories",
            headers=auth_headers
        ).json()
        
        for cat in cats:
            if "TEST_" in cat["name"]:
                requests.delete(
                    f"{BASE_URL}/api/restaurants/{RESTAURANT_ID_2}/categories/{cat['id']}",
                    headers=auth_headers
                )
        
        # Cleanup labels in restaurant 1
        labels = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/labels",
            headers=auth_headers
        ).json()
        
        for label in labels:
            if "TEST_" in label["name"]:
                requests.delete(
                    f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/labels/{label['id']}",
                    headers=auth_headers
                )
        
        # Cleanup items in restaurant 1
        items = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/menu-items",
            headers=auth_headers
        ).json()
        
        for item in items:
            if "TEST_" in item["name"]:
                requests.delete(
                    f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/menu-items/{item['id']}",
                    headers=auth_headers
                )
        
        # Cleanup categories in restaurant 1
        cats1 = requests.get(
            f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/categories",
            headers=auth_headers
        ).json()
        
        for cat in cats1:
            if "TEST_" in cat["name"]:
                requests.delete(
                    f"{BASE_URL}/api/restaurants/{RESTAURANT_ID}/categories/{cat['id']}",
                    headers=auth_headers
                )
        
        print("SUCCESS: Cleaned up TEST_ prefixed data")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
