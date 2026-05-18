"""Tests for POST /api/restaurants/{rid}/categories/bulk-rename endpoint."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://restaurant-hub-275.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_USER = "admin"
ADMIN_PASS = "220066"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS}, timeout=15)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    assert tok, f"No token in response: {data}"
    return tok


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def restaurant_id(headers):
    r = requests.get(f"{API}/restaurants", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    restaurants = r.json()
    assert len(restaurants) > 0, "No restaurants found"
    # Prefer non-demo
    for rest in restaurants:
        if rest.get("slug") != "demo":
            return rest["id"]
    return restaurants[0]["id"]


@pytest.fixture
def temp_categories(headers, restaurant_id):
    """Create 3 temp categories, return their ids; cleanup afterwards."""
    created = []
    for i in range(3):
        payload = {"name": f"TEST_BulkRename_Cat_{i}_{int(time.time())}"}
        r = requests.post(
            f"{API}/restaurants/{restaurant_id}/categories",
            headers=headers,
            json=payload,
            timeout=15,
        )
        assert r.status_code in (200, 201), r.text
        created.append(r.json())
    yield created
    for c in created:
        try:
            requests.delete(
                f"{API}/restaurants/{restaurant_id}/categories/{c['id']}",
                headers=headers,
                timeout=10,
            )
        except Exception:
            pass


def test_bulk_rename_requires_auth(restaurant_id):
    r = requests.post(
        f"{API}/restaurants/{restaurant_id}/categories/bulk-rename",
        json=[{"id": "x", "name": "y"}],
        timeout=15,
    )
    assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"


def test_bulk_rename_happy_path(headers, restaurant_id, temp_categories):
    renames = [{"id": c["id"], "name": f"Renamed_{i}_{int(time.time())}"} for i, c in enumerate(temp_categories)]
    r = requests.post(
        f"{API}/restaurants/{restaurant_id}/categories/bulk-rename",
        headers=headers,
        json=renames,
        timeout=20,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["updated"] == 3, f"Expected 3 updated, got {data}"
    assert data["skipped"] == 0

    # Verify persistence via GET
    r2 = requests.get(f"{API}/restaurants/{restaurant_id}/categories", headers=headers, timeout=15)
    assert r2.status_code == 200
    all_cats = {c["id"]: c for c in r2.json()}
    for entry in renames:
        cat = all_cats.get(entry["id"])
        assert cat is not None, f"Category {entry['id']} missing"
        assert cat["name"] == entry["name"], f"Name not persisted: {cat}"
        # Translations should be reset
        assert cat.get("name_en", "") == "", f"name_en not reset: {cat}"
        assert cat.get("name_zh", "") == "", f"name_zh not reset: {cat}"


def test_bulk_rename_skips_invalid_items(headers, restaurant_id, temp_categories):
    valid_id = temp_categories[0]["id"]
    renames = [
        {"id": valid_id, "name": f"ValidName_{int(time.time())}"},
        {"id": valid_id, "name": "   "},  # empty after strip -> skipped
        {"id": "", "name": "NoId"},  # no id -> skipped
        {"name": "MissingId"},  # missing id -> skipped
        {"id": "non-existent-id-xyz-12345", "name": "Ghost"},  # unknown -> skipped
        {},  # empty -> skipped
    ]
    r = requests.post(
        f"{API}/restaurants/{restaurant_id}/categories/bulk-rename",
        headers=headers,
        json=renames,
        timeout=20,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["updated"] == 1, f"Expected 1 updated, got {data}"
    assert data["skipped"] == 5, f"Expected 5 skipped, got {data}"


def test_bulk_rename_empty_list(headers, restaurant_id):
    r = requests.post(
        f"{API}/restaurants/{restaurant_id}/categories/bulk-rename",
        headers=headers,
        json=[],
        timeout=15,
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"updated": 0, "skipped": 0}


def test_bulk_rename_other_restaurant_categories_skipped(headers, restaurant_id, temp_categories):
    """If rid in URL doesn't match the category's restaurant_id, should be skipped."""
    # Use a fake restaurant id
    r = requests.post(
        f"{API}/restaurants/fake-rid-99999/categories/bulk-rename",
        headers=headers,
        json=[{"id": temp_categories[0]["id"], "name": "ShouldNotApply"}],
        timeout=20,
    )
    # check_restaurant_access likely raises 403/404 for unknown rid
    assert r.status_code in (200, 403, 404), r.text
    if r.status_code == 200:
        assert r.json()["updated"] == 0
        assert r.json()["skipped"] == 1
