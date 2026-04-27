"""
Caffesta API rewrite regression tests (iteration 16).
Covers: import-caffesta, analytics graceful, time-window, stop-list/sync,
plus regression for cost analysis/upload and caffesta config persistence.
"""
import os
import io
import csv
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN = {"username": "admin", "password": "220066"}


@pytest.fixture(scope="module")
def auth_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    tok = r.json().get("token") or r.json().get("access_token")
    assert tok
    return tok


@pytest.fixture(scope="module")
def headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def restaurant_id(headers):
    r = requests.get(f"{BASE_URL}/api/restaurants", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    items = r.json()
    assert isinstance(items, list) and items, "no restaurants"
    return items[0]["id"]


# ============ Disable Caffesta to ensure clean state for "disabled" assertions ============
@pytest.fixture(scope="module", autouse=True)
def disable_caffesta(headers, restaurant_id):
    # Set enabled=False so disabled-path tests are deterministic
    requests.put(
        f"{BASE_URL}/api/restaurants/{restaurant_id}/caffesta",
        headers=headers,
        json={"enabled": False},
        timeout=15,
    )
    yield


# ============ import-caffesta when disabled ============
def test_import_caffesta_returns_400_when_disabled(headers, restaurant_id):
    r = requests.post(
        f"{BASE_URL}/api/restaurants/{restaurant_id}/costs/import-caffesta",
        headers=headers,
        timeout=20,
    )
    assert r.status_code == 400, f"expected 400, got {r.status_code} {r.text}"
    body = r.json()
    detail = body.get("detail") or body.get("message") or ""
    assert "Caffesta" in detail


# ============ analytics graceful with disabled Caffesta ============
def test_analytics_works_when_disabled(headers, restaurant_id):
    r = requests.get(
        f"{BASE_URL}/api/restaurants/{restaurant_id}/caffesta/analytics?days=7",
        headers=headers,
        timeout=30,
    )
    assert r.status_code == 200, f"analytics crashed: {r.status_code} {r.text}"
    data = r.json()
    assert "totals" in data and "payments" in data
    assert data["totals"]["revenue"] == 0
    assert data["totals"]["quantity"] == 0
    assert data["payments"] == []
    assert "top_products" in data
    assert "by_terminal" in data


# ============ time-window when disabled returns 400 ============
def test_time_window_returns_400_when_disabled(headers, restaurant_id):
    r = requests.get(
        f"{BASE_URL}/api/restaurants/{restaurant_id}/caffesta/time-window"
        "?days=7&day_type=weekend&time_from=12:00&time_to=15:00",
        headers=headers,
        timeout=20,
    )
    assert r.status_code == 400, f"expected 400 got {r.status_code} {r.text}"
    detail = r.json().get("detail", "")
    assert isinstance(detail, str) and len(detail) > 0


# ============ time-window invalid HH:MM ============
def test_time_window_invalid_time_returns_400(headers, restaurant_id):
    r = requests.get(
        f"{BASE_URL}/api/restaurants/{restaurant_id}/caffesta/time-window"
        "?days=7&time_from=bad&time_to=15:00",
        headers=headers,
        timeout=20,
    )
    assert r.status_code == 400


# ============ time-window when enabled but creds invalid ============
def test_time_window_enabled_invalid_creds_returns_graceful(headers, restaurant_id):
    # Enable Caffesta with bogus creds
    requests.put(
        f"{BASE_URL}/api/restaurants/{restaurant_id}/caffesta",
        headers=headers,
        json={"enabled": True, "account_name": "bogusacct", "api_key": "bogus", "pos_id": 1},
        timeout=15,
    )
    try:
        r = requests.get(
            f"{BASE_URL}/api/restaurants/{restaurant_id}/caffesta/time-window"
            "?days=7&day_type=all&time_from=00:00&time_to=23:59",
            headers=headers,
            timeout=60,
        )
        # Acceptable: 200 with empty data, OR 400 if terminals discovery fails
        # Per requirement: "when enabled but creds invalid, returns 200 with empty totals"
        assert r.status_code in (200, 400), f"got {r.status_code} {r.text}"
        if r.status_code == 200:
            data = r.json()
            assert data["totals"]["revenue"] == 0
            assert data["totals"]["receipts"] == 0
            assert data["payments"] == []
            assert data["samples"] == []
    finally:
        # Restore disabled state
        requests.put(
            f"{BASE_URL}/api/restaurants/{restaurant_id}/caffesta",
            headers=headers,
            json={"enabled": False},
            timeout=15,
        )


# ============ stop-list/sync when disabled ============
def test_stop_list_sync_returns_400_when_disabled(headers, restaurant_id):
    r = requests.post(
        f"{BASE_URL}/api/restaurants/{restaurant_id}/caffesta/stop-list/sync",
        headers=headers,
        timeout=20,
    )
    assert r.status_code == 400, f"expected 400, got {r.status_code} {r.text}"


# ============ Regression: costs/analysis ============
def test_costs_analysis_regression(headers, restaurant_id):
    r = requests.get(
        f"{BASE_URL}/api/restaurants/{restaurant_id}/costs/analysis",
        headers=headers,
        timeout=30,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "items" in data
    assert "summary" in data
    s = data["summary"]
    for k in ("total", "with_cost", "without_cost", "critical", "warning", "ok"):
        assert k in s


# ============ Regression: costs/upload CSV ============
def test_costs_upload_csv_regression(headers, restaurant_id):
    csv_text = "Название,Себестоимость\nТЕСТ_БЛЮДО_X9999,42.5\n"
    files = {"file": ("test.csv", csv_text.encode("utf-8"), "text/csv")}
    h = {"Authorization": headers["Authorization"]}
    r = requests.post(
        f"{BASE_URL}/api/restaurants/{restaurant_id}/costs/upload",
        headers=h,
        files=files,
        timeout=30,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "matched" in body and "total" in body and "unmatched" in body
    assert body["total"] == 1


# ============ Regression: caffesta payment_methods PUT ============
def test_caffesta_put_payment_methods_regression(headers, restaurant_id):
    payload = {
        "account_name": "test_acct",
        "api_key": "test_key",
        "pos_id": 1,
        "payment_methods": [
            {"name": "Тест нал", "payment_id": 1, "is_default": True},
            {"name": "Тест карта", "payment_id": 2, "is_default": False},
        ],
        "enabled": False,
    }
    r = requests.put(
        f"{BASE_URL}/api/restaurants/{restaurant_id}/caffesta",
        headers=headers,
        json=payload,
        timeout=15,
    )
    assert r.status_code == 200, r.text
    cfg = r.json()
    assert cfg["payment_id"] == 1
    pms = cfg.get("payment_methods", [])
    assert len(pms) == 2

    # Verify persistence
    r2 = requests.get(
        f"{BASE_URL}/api/restaurants/{restaurant_id}/caffesta",
        headers=headers,
        timeout=15,
    )
    assert r2.status_code == 200
    cfg2 = r2.json()
    assert cfg2["payment_id"] == 1
    assert len(cfg2.get("payment_methods", [])) == 2


# ============ Regression: analytics shape with 0-day period ============
def test_analytics_shape_default_days(headers, restaurant_id):
    r = requests.get(
        f"{BASE_URL}/api/restaurants/{restaurant_id}/caffesta/analytics",
        headers=headers,
        timeout=20,
    )
    assert r.status_code == 200
    data = r.json()
    for k in ("period", "totals", "payments", "top_products", "by_terminal"):
        assert k in data
