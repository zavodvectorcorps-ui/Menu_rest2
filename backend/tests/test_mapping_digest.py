"""
Tests for new features in iteration 17:
- Caffesta auto-mapping (fuzzy suggest + batch apply)
- Daily Telegram digest (preview + send)
- Settings persistence for digest fields
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

RESTAURANT_ID = "aa25189d-d668-4838-915a-c5d936547f3f"


@pytest.fixture(scope="session")
def token():
    r = requests.post(f"{API}/auth/login", json={"username": "admin", "password": "220066"}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def client(token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return s


# ---------- Auto-mapping suggest ----------
class TestAutoMappingSuggest:
    def test_suggest_caffesta_disabled(self, client):
        # Ensure Caffesta disabled (it should be by default from seed)
        client.put(f"{API}/restaurants/{RESTAURANT_ID}/caffesta", json={"enabled": False, "account_name": "", "api_key": ""})
        r = client.get(f"{API}/restaurants/{RESTAURANT_ID}/caffesta/auto-mapping/suggest?threshold=60")
        # Acceptable: 400 with message OR 200 with empty suggestions
        assert r.status_code in (200, 400), r.text
        if r.status_code == 200:
            data = r.json()
            assert "suggestions" in data
            assert isinstance(data["suggestions"], list)
        else:
            assert "detail" in r.json()

    def test_suggest_with_params(self, client):
        r = client.get(
            f"{API}/restaurants/{RESTAURANT_ID}/caffesta/auto-mapping/suggest",
            params={"threshold": 60, "only_unmapped": "true"},
        )
        assert r.status_code in (200, 400)

    def test_suggest_only_unmapped_false(self, client):
        r = client.get(
            f"{API}/restaurants/{RESTAURANT_ID}/caffesta/auto-mapping/suggest",
            params={"threshold": 50, "only_unmapped": "false"},
        )
        assert r.status_code in (200, 400)


# ---------- Auto-mapping apply ----------
class TestAutoMappingApply:
    def test_apply_empty(self, client):
        r = client.post(f"{API}/restaurants/{RESTAURANT_ID}/caffesta/auto-mapping/apply", json={"mappings": []})
        assert r.status_code == 200
        assert r.json() == {"updated": 0, "total": 0}

    def test_apply_set_and_unset(self, client):
        # Get some menu item
        items_res = client.get(f"{API}/restaurants/{RESTAURANT_ID}/menu-items")
        assert items_res.status_code == 200
        items = items_res.json()
        assert len(items) > 0, "Need at least one menu item for this test"
        item = items[0]
        item_id = item["id"]
        original_caffesta_id = item.get("caffesta_product_id")

        # Set caffesta_product_id = 99999
        apply_res = client.post(
            f"{API}/restaurants/{RESTAURANT_ID}/caffesta/auto-mapping/apply",
            json={"mappings": [{"menu_item_id": item_id, "caffesta_product_id": 99999}]},
        )
        assert apply_res.status_code == 200, apply_res.text
        body = apply_res.json()
        assert body["total"] == 1

        # Verify via GET
        verify = client.get(f"{API}/restaurants/{RESTAURANT_ID}/menu-items")
        got = next((x for x in verify.json() if x["id"] == item_id), None)
        assert got is not None
        assert got.get("caffesta_product_id") == 99999

        # Unlink (set None)
        unlink = client.post(
            f"{API}/restaurants/{RESTAURANT_ID}/caffesta/auto-mapping/apply",
            json={"mappings": [{"menu_item_id": item_id, "caffesta_product_id": None}]},
        )
        assert unlink.status_code == 200
        verify2 = client.get(f"{API}/restaurants/{RESTAURANT_ID}/menu-items")
        got2 = next((x for x in verify2.json() if x["id"] == item_id), None)
        assert got2.get("caffesta_product_id") in (None, "")

        # Restore original
        client.post(
            f"{API}/restaurants/{RESTAURANT_ID}/caffesta/auto-mapping/apply",
            json={"mappings": [{"menu_item_id": item_id, "caffesta_product_id": original_caffesta_id}]},
        )


# ---------- Digest preview ----------
class TestDigestPreview:
    def test_preview_returns_text(self, client):
        r = client.get(f"{API}/restaurants/{RESTAURANT_ID}/digest/preview")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "text" in data
        text = data["text"]
        assert isinstance(text, str)
        assert len(text) > 0
        # Structural checks
        assert "Выручка" in text
        assert "Чеков" in text
        assert "Средний чек" in text
        assert "По окнам" in text

    def test_preview_no_500_when_caffesta_disabled(self, client):
        # Already disabled in earlier tests
        r = client.get(f"{API}/restaurants/{RESTAURANT_ID}/digest/preview")
        assert r.status_code == 200


# ---------- Digest send ----------
class TestDigestSend:
    def test_send_no_credentials_returns_400(self, client):
        # Clear digest creds
        client.put(
            f"{API}/restaurants/{RESTAURANT_ID}/settings",
            json={
                "daily_digest_enabled": False,
                "daily_digest_bot_token": "",
                "daily_digest_chat_id": "",
                # Also clear telegram fallback ones to ensure 'no-credentials' path
                "telegram_bot_token": "",
                "telegram_chat_id": "",
            },
        )
        r = client.post(f"{API}/restaurants/{RESTAURANT_ID}/digest/send")
        assert r.status_code == 400, r.text
        assert "no-credentials" in r.json().get("detail", "")


# ---------- Settings persistence ----------
class TestDigestSettingsPersist:
    def test_put_and_get_settings_roundtrip(self, client):
        payload = {
            "daily_digest_enabled": True,
            "daily_digest_bot_token": "TEST_TOKEN_123",
            "daily_digest_chat_id": "TEST_CHAT_456",
            "daily_digest_windows": [
                {"name": "Завтрак", "time_from": "08:00", "time_to": "12:00"},
                {"name": "Обед", "time_from": "12:00", "time_to": "16:00"},
                {"name": "Вечер", "time_from": "18:00", "time_to": "23:00"},
            ],
        }
        r = client.put(f"{API}/restaurants/{RESTAURANT_ID}/settings", json=payload)
        assert r.status_code == 200, r.text

        got = client.get(f"{API}/restaurants/{RESTAURANT_ID}/settings")
        assert got.status_code == 200
        body = got.json()
        assert body.get("daily_digest_enabled") is True
        assert body.get("daily_digest_bot_token") == "TEST_TOKEN_123"
        assert body.get("daily_digest_chat_id") == "TEST_CHAT_456"
        assert len(body.get("daily_digest_windows") or []) == 3
        assert body["daily_digest_windows"][0]["name"] == "Завтрак"

    def test_teardown_disable_digest(self, client):
        # Cleanup: restore to safe state
        client.put(
            f"{API}/restaurants/{RESTAURANT_ID}/settings",
            json={
                "daily_digest_enabled": False,
                "daily_digest_bot_token": "",
                "daily_digest_chat_id": "",
            },
        )


# ---------- Regression ----------
class TestRegression:
    def test_caffesta_time_window_still_works(self, client):
        r = client.get(
            f"{API}/restaurants/{RESTAURANT_ID}/caffesta/time-window",
            params={"time_from": "10:00", "time_to": "14:00", "days": 7},
        )
        # Disabled -> 400 (consistent with iter16)
        assert r.status_code in (200, 400)

    def test_costs_analysis_still_works(self, client):
        r = client.get(f"{API}/restaurants/{RESTAURANT_ID}/costs/analysis")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "summary" in data
