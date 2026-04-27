"""
Tests for:
  - Price Control / Margin Analysis (cost_control.py endpoints)
  - Caffesta payment_methods config (caffesta.py)
  - Caffesta /time-window endpoint (caffesta.py)

Note: Caffesta external API is not reachable in test env.
Endpoints that proxy to Caffesta should respond gracefully (400 / errors), NOT 500.
"""
import io
import os
import csv
import pytest
import requests
from openpyxl import Workbook

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://margin-control-4.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


# ---------------- fixtures ----------------
@pytest.fixture(scope="module")
def auth_token():
    r = requests.post(f"{API}/auth/login", json={"username": "admin", "password": "220066"}, timeout=15)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def restaurant_id(headers):
    r = requests.get(f"{API}/restaurants", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data) > 0, "No restaurants found"
    return data[0]["id"]


@pytest.fixture(scope="module")
def menu_items(headers, restaurant_id):
    r = requests.get(f"{API}/restaurants/{restaurant_id}/menu-items", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    return [it for it in r.json() if not it.get("is_banner")]


@pytest.fixture(scope="module")
def categories(headers, restaurant_id):
    r = requests.get(f"{API}/restaurants/{restaurant_id}/categories", headers=headers, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


# ---------------- Cost Control / Analysis ----------------
class TestCostsAnalysis:
    def test_analysis_returns_items_and_summary(self, headers, restaurant_id):
        r = requests.get(f"{API}/restaurants/{restaurant_id}/costs/analysis", headers=headers, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data and isinstance(data["items"], list)
        assert "summary" in data
        s = data["summary"]
        for k in ("total", "with_cost", "without_cost", "critical", "warning", "ok"):
            assert k in s, f"Missing summary key: {k}"
        # Items shape
        if data["items"]:
            it = data["items"][0]
            for k in ("id", "name", "price", "cost_price", "margin_pct", "threshold", "threshold_source", "status"):
                assert k in it, f"Item missing key: {k}"
            assert it["status"] in ("ok", "warning", "critical", "no-cost", "no-price")
            assert it["threshold_source"] in ("item", "category", "default")


# ---------------- Cost upload (CSV / XLSX) ----------------
class TestCostsUpload:
    def test_upload_csv_matches_existing_items(self, auth_token, restaurant_id, menu_items):
        # Pick first 3 items with valid name
        sample = [it for it in menu_items if it.get("name")][:3]
        if not sample:
            pytest.skip("No menu items to upload costs for")

        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["Название", "Себестоимость"])
        for i, it in enumerate(sample):
            w.writerow([it["name"], 100 + i * 10])
        # Add unmatched line
        w.writerow(["TEST_NONEXISTENT_ITEM_XYZ", 999])
        content = buf.getvalue().encode("utf-8-sig")

        files = {"file": ("costs.csv", content, "text/csv")}
        r = requests.post(
            f"{API}/restaurants/{restaurant_id}/costs/upload",
            headers={"Authorization": f"Bearer {auth_token}"},
            files=files,
            timeout=30,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["total"] == len(sample) + 1
        assert data["matched"] >= len(sample), f"Expected to match {len(sample)} items, got {data['matched']}"
        assert isinstance(data["unmatched"], list)

    def test_upload_xlsx_matches_existing_items(self, auth_token, restaurant_id, menu_items):
        sample = [it for it in menu_items if it.get("name")][:2]
        if not sample:
            pytest.skip("No menu items to upload costs for")

        wb = Workbook()
        ws = wb.active
        ws.append(["Название", "Себестоимость"])
        for i, it in enumerate(sample):
            ws.append([it["name"], 50 + i * 5])
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)

        files = {"file": (
            "costs.xlsx",
            bio.getvalue(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )}
        r = requests.post(
            f"{API}/restaurants/{restaurant_id}/costs/upload",
            headers={"Authorization": f"Bearer {auth_token}"},
            files=files,
            timeout=30,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["total"] == len(sample)
        assert data["matched"] >= 1

    def test_upload_empty_returns_400(self, auth_token, restaurant_id):
        files = {"file": ("empty.csv", b"", "text/csv")}
        r = requests.post(
            f"{API}/restaurants/{restaurant_id}/costs/upload",
            headers={"Authorization": f"Bearer {auth_token}"},
            files=files,
            timeout=15,
        )
        assert r.status_code == 400


# ---------------- Item / category cost & threshold ----------------
class TestItemAndCategoryUpdate:
    def test_update_item_cost_and_threshold(self, headers, restaurant_id, menu_items):
        if not menu_items:
            pytest.skip("No menu items")
        item_id = menu_items[0]["id"]
        payload = {"cost_price": 123.45, "margin_threshold": 40}
        r = requests.put(
            f"{API}/restaurants/{restaurant_id}/menu-items/{item_id}/cost",
            headers=headers, json=payload, timeout=15,
        )
        assert r.status_code == 200, r.text
        assert r.json().get("updated") is True

        # Verify via analysis
        r2 = requests.get(f"{API}/restaurants/{restaurant_id}/costs/analysis", headers=headers, timeout=15)
        items = r2.json()["items"]
        target = next((x for x in items if x["id"] == item_id), None)
        assert target is not None
        assert target["cost_price"] == 123.45
        assert target["threshold"] == 40
        assert target["threshold_source"] == "item"

    def test_update_category_threshold(self, headers, restaurant_id, categories):
        if not categories:
            pytest.skip("No categories")
        cat_id = categories[0]["id"]
        r = requests.put(
            f"{API}/restaurants/{restaurant_id}/categories/{cat_id}/threshold",
            headers=headers, json={"margin_threshold": 25}, timeout=15,
        )
        assert r.status_code == 200, r.text
        assert r.json().get("updated") is True

    def test_update_item_empty_payload_returns_400(self, headers, restaurant_id, menu_items):
        if not menu_items:
            pytest.skip("No menu items")
        item_id = menu_items[0]["id"]
        r = requests.put(
            f"{API}/restaurants/{restaurant_id}/menu-items/{item_id}/cost",
            headers=headers, json={}, timeout=15,
        )
        assert r.status_code == 400


# ---------------- Alerts trigger (no-op if disabled) ----------------
class TestAlertsTrigger:
    def test_check_alerts_succeeds_when_disabled(self, headers, restaurant_id):
        r = requests.post(
            f"{API}/restaurants/{restaurant_id}/costs/check-alerts",
            headers=headers, timeout=15,
        )
        assert r.status_code == 200, r.text
        assert r.json().get("sent") is True


# ---------------- Caffesta config & payment_methods ----------------
class TestCaffestaConfig:
    def test_get_caffesta_returns_payment_methods_field(self, headers, restaurant_id):
        r = requests.get(f"{API}/restaurants/{restaurant_id}/caffesta", headers=headers, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "payment_methods" in data
        assert isinstance(data["payment_methods"], list)

    def test_put_caffesta_payment_methods_persists_and_syncs_default(self, headers, restaurant_id):
        methods = [
            {"name": "Наличные", "payment_id": 1, "is_default": False},
            {"name": "Карта", "payment_id": 2, "is_default": True},
            {"name": "Перевод", "payment_id": 3, "is_default": False},
        ]
        r = requests.put(
            f"{API}/restaurants/{restaurant_id}/caffesta",
            headers=headers, json={"payment_methods": methods}, timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data.get("payment_methods"), list)
        assert len(data["payment_methods"]) == 3
        names = [m["name"] for m in data["payment_methods"]]
        assert "Карта" in names
        # Legacy payment_id should sync with default
        assert data.get("payment_id") == 2

        # GET to verify persistence
        r2 = requests.get(f"{API}/restaurants/{restaurant_id}/caffesta", headers=headers, timeout=15)
        d2 = r2.json()
        assert len(d2["payment_methods"]) == 3
        default = next((m for m in d2["payment_methods"] if m["is_default"]), None)
        assert default is not None
        assert default["payment_id"] == 2

    def test_put_caffesta_payment_methods_no_default_uses_first(self, headers, restaurant_id):
        methods = [
            {"name": "Только наличные", "payment_id": 5, "is_default": False},
            {"name": "Только карта", "payment_id": 6, "is_default": False},
        ]
        r = requests.put(
            f"{API}/restaurants/{restaurant_id}/caffesta",
            headers=headers, json={"payment_methods": methods}, timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("payment_id") == 5


# ---------------- Caffesta time-window ----------------
class TestCaffestaTimeWindow:
    def test_time_window_returns_400_when_disabled(self, headers, restaurant_id):
        # Caffesta is disabled in test env -> service returns ok=False -> 400
        r = requests.get(
            f"{API}/restaurants/{restaurant_id}/caffesta/time-window",
            params={"days": 7, "day_type": "all", "time_from": "00:00", "time_to": "23:59"},
            headers=headers, timeout=20,
        )
        # Should NOT be 500 — should respond 400 with proper detail
        assert r.status_code in (400, 200), f"Unexpected status {r.status_code}: {r.text}"
        if r.status_code == 400:
            data = r.json()
            assert "detail" in data
            assert isinstance(data["detail"], str) and len(data["detail"]) > 0

    def test_time_window_invalid_time_format(self, headers, restaurant_id):
        r = requests.get(
            f"{API}/restaurants/{restaurant_id}/caffesta/time-window",
            params={"days": 7, "day_type": "all", "time_from": "bad", "time_to": "23:59"},
            headers=headers, timeout=15,
        )
        # Either 400 from Caffesta-disabled (handled first) OR 400 from time format
        assert r.status_code == 400, r.text

    def test_time_window_accepts_valid_day_types(self, headers, restaurant_id):
        # Each call should return a deterministic 400 (Caffesta disabled) — not 500
        for dt in ("all", "weekday", "weekend"):
            r = requests.get(
                f"{API}/restaurants/{restaurant_id}/caffesta/time-window",
                params={"days": 7, "day_type": dt, "time_from": "00:00", "time_to": "02:00"},
                headers=headers, timeout=20,
            )
            assert r.status_code in (200, 400), f"day_type={dt}: {r.status_code} {r.text}"
