"""Tests for nutrition (БЖУ) fields on menu items (iteration 24/25)."""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://restaurant-hub-275.preview.emergentagent.com").rstrip("/")


@pytest.fixture(scope="module")
def auth_headers():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": "admin", "password": "220066"})
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    tok = r.json().get("access_token") or r.json().get("token")
    assert tok, f"No token in {r.json()}"
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def restaurant_id(auth_headers):
    r = requests.get(f"{BASE_URL}/api/restaurants", headers=auth_headers)
    assert r.status_code == 200
    rests = r.json()
    assert rests, "No restaurants found"
    # Prefer /demo/1 restaurant if id "1"
    for rest in rests:
        if rest.get("id") == "1":
            return "1"
    return rests[0]["id"]


@pytest.fixture(scope="module")
def category_id(auth_headers, restaurant_id):
    r = requests.get(f"{BASE_URL}/api/restaurants/{restaurant_id}/categories", headers=auth_headers)
    assert r.status_code == 200
    cats = r.json()
    assert cats, "No categories found"
    return cats[0]["id"]


NUTRI_ITEM_IDS = []


def test_create_item_with_nutrition(auth_headers, restaurant_id, category_id):
    payload = {
        "category_id": category_id,
        "name": "NUTRI_E2E_TEST",
        "price": 10.0,
        "nutrition_protein": 20.5,
        "nutrition_fat": 12,
        "nutrition_carbs": 5.2,
        "nutrition_kcal": 210,
        "nutrition_kj": 880,
    }
    r = requests.post(f"{BASE_URL}/api/restaurants/{restaurant_id}/menu-items", json=payload, headers=auth_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["nutrition_protein"] == 20.5
    assert data["nutrition_fat"] == 12
    assert data["nutrition_carbs"] == 5.2
    assert data["nutrition_kcal"] == 210
    assert data["nutrition_kj"] == 880
    NUTRI_ITEM_IDS.append(data["id"])


def test_update_item_nutrition(auth_headers, restaurant_id):
    assert NUTRI_ITEM_IDS, "Create test must run first"
    item_id = NUTRI_ITEM_IDS[0]
    r = requests.put(
        f"{BASE_URL}/api/restaurants/{restaurant_id}/menu-items/{item_id}",
        json={"nutrition_protein": 25},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    # GET verify
    r2 = requests.get(f"{BASE_URL}/api/restaurants/{restaurant_id}/menu-items", headers=auth_headers)
    assert r2.status_code == 200
    match = [i for i in r2.json() if i["id"] == item_id]
    assert match, "Item not found after update"
    it = match[0]
    assert it["nutrition_protein"] == 25
    assert it["nutrition_fat"] == 12  # untouched


def test_create_item_without_nutrition_returns_null(auth_headers, restaurant_id, category_id):
    payload = {"category_id": category_id, "name": "NUTRI_E2E_TEST_NULL", "price": 5.0}
    r = requests.post(f"{BASE_URL}/api/restaurants/{restaurant_id}/menu-items", json=payload, headers=auth_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    for k in ("nutrition_protein", "nutrition_fat", "nutrition_carbs", "nutrition_kcal", "nutrition_kj"):
        assert k in data, f"Missing key {k}"
        assert data[k] is None, f"Expected {k} to be None, got {data[k]!r}"
    NUTRI_ITEM_IDS.append(data["id"])


def test_cleanup_delete_null_item(auth_headers, restaurant_id):
    # Delete only the null item; keep NUTRI_E2E_TEST for frontend test
    if len(NUTRI_ITEM_IDS) < 2:
        pytest.skip("no null item created")
    r = requests.delete(
        f"{BASE_URL}/api/restaurants/{restaurant_id}/menu-items/{NUTRI_ITEM_IDS[1]}",
        headers=auth_headers,
    )
    assert r.status_code == 200
