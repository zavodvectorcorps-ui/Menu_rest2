"""
Iteration 33 — verification of the naive/aware datetime fix in
`services.loyalty_sync.run_loyalty_sync_job`.

Bug: `now = datetime.now(timezone.utc)` (aware) minus `cfg['last_polled_at']`
(naive, from BSON) raised TypeError "can't subtract offset-naive and
offset-aware datetimes", caught by the outer catch → `_sync_one` never ran.

Covered here:
* run_loyalty_sync_job with NAIVE last_polled_at → no TypeError, _sync_one called,
  last_polled_at refreshed
* run_loyalty_sync_job with AWARE last_polled_at → backwards compatible
* interval throttling still works with naive timestamps (recent poll → skip)
* naive `last_synced_at` fallback (no last_polled_at at all)
* POST /api/.../loyalty/sync-now works regardless of tzinfo
* regression: category is_active toggle (iteration 30)

Caffesta HTTP calls are monkeypatched — the preview env has no valid X-API-KEY.
Original loyalty_config document is restored in teardown.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest
import requests
from dotenv import dotenv_values

sys.path.insert(0, "/app/backend")

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing from env and /app/frontend/.env")
BASE_URL = base_url.rstrip("/")

RID = "aa25189d-d668-4838-915a-c5d936547f3f"
CAT_ID = "768fe425-3b91-40c4-9df9-0090f2b3ed06"
USERNAME = "admin"
PASSWORD = "220066"

NAIVE_ERR = "can't subtract offset-naive and offset-aware datetimes"


# ─── helpers ───────────────────────────────────────────────────────────────

def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


@pytest.fixture(scope="module")
def mod():
    """Import backend modules in-process (motor client per call is fine)."""
    import services.loyalty_sync as ls
    from database import db
    from services.loyalty_crypto import encrypt
    return {"ls": ls, "db": db, "encrypt": encrypt}


@pytest.fixture(scope="module")
def http():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"username": USERNAME, "password": PASSWORD}, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"login failed {r.status_code}: {r.text[:300]}")
    token = r.json().get("access_token") or r.json().get("token")
    if not token:
        pytest.fail(f"no token in login response: {r.json()}")
    s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module", autouse=True)
def preserve_config(mod):
    """Snapshot loyalty_config for RID and restore it after the module."""
    db = mod["db"]
    original = _run(db.loyalty_config.find_one({"restaurant_id": RID}))
    yield original
    if original is not None:
        original.pop("_id", None)
        _run(db.loyalty_config.replace_one({"restaurant_id": RID}, original, upsert=True))
    else:
        _run(db.loyalty_config.delete_one({"restaurant_id": RID}))


def _seed(mod, last_polled_at, *, last_synced_at=None, interval=1, enabled=True):
    db, encrypt = mod["db"], mod["encrypt"]
    doc = {
        "restaurant_id": RID,
        "is_enabled": enabled,
        "sync_interval_min": interval,
        "caffesta_account_name": "TEST_account",
        "caffesta_api_key_enc": encrypt("TEST_key"),
        "pos_id": "TEST_pos",
        "telegram_bot_token_enc": encrypt("TEST_token"),
        "template_accrual": "+{amount}, баланс {balance}",
        "template_debit": "-{amount}, баланс {balance}",
        "last_clients_ts": 1000,
        "last_polled_at": last_polled_at,
        "last_synced_at": last_synced_at,
        "last_error": "",
        "last_error_at": None,
    }
    _run(db.loyalty_config.update_one({"restaurant_id": RID}, {"$set": doc}, upsert=True))
    return doc


def _get_cfg(mod):
    return _run(mod["db"].loyalty_config.find_one({"restaurant_id": RID}, {"_id": 0}))


class _Capture:
    """Capture records from the loyalty.sync logger + root."""

    def __init__(self):
        self.records = []

    def __enter__(self):
        self.handler = logging.Handler()
        self.handler.emit = lambda rec: self.records.append(rec)
        for name in ("loyalty.sync", ""):
            logging.getLogger(name).addHandler(self.handler)
        return self

    def __exit__(self, *a):
        for name in ("loyalty.sync", ""):
            logging.getLogger(name).removeHandler(self.handler)

    def text(self):
        out = []
        for rec in self.records:
            try:
                out.append(rec.getMessage())
            except Exception:
                out.append(str(rec.msg))
            if rec.exc_info:
                import traceback
                out.append("".join(traceback.format_exception(*rec.exc_info)))
        return "\n".join(out)


def _patch_caffesta(mod, monkeypatch, clients_ts=2000, client_list=None):
    """Avoid real Caffesta network calls."""
    ls = mod["ls"]
    calls = {"get_updates": 0, "get_clients": 0}

    async def fake_updates(account_name, api_key, pos_id):
        calls["get_updates"] += 1
        return {"data": {"clients": clients_ts}}

    async def fake_clients(account_name, api_key, since_ts):
        calls["get_clients"] += 1
        return client_list if client_list is not None else []

    monkeypatch.setattr(ls, "caffesta_get_updates", fake_updates)
    monkeypatch.setattr(ls, "caffesta_get_clients", fake_clients)
    return calls


# ─── tests ─────────────────────────────────────────────────────────────────

class TestNaiveDatetimeFix:

    def test_naive_last_polled_at_does_not_raise(self, mod, monkeypatch):
        """Core bug: naive last_polled_at from BSON must not blow up the tick."""
        naive_old = datetime.utcnow() - timedelta(minutes=5)
        assert naive_old.tzinfo is None
        _seed(mod, naive_old)
        stored = _get_cfg(mod)
        assert stored["last_polled_at"].tzinfo is None, "seed must be naive in Mongo"

        calls = _patch_caffesta(mod, monkeypatch)
        with _Capture() as cap:
            _run(mod["ls"].run_loyalty_sync_job())
        log = cap.text()

        assert NAIVE_ERR not in log, f"offset-naive TypeError still raised:\n{log}"
        assert "outer catch" not in log, f"outer catch triggered:\n{log}"
        # _sync_one really ran
        assert calls["get_updates"] >= 1, "_sync_one was NOT called (get_updates never hit)"

        after = _get_cfg(mod)
        polled = after["last_polled_at"]
        assert polled is not None
        polled_aware = polled if polled.tzinfo else polled.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - polled_aware).total_seconds()
        assert age < 60, f"last_polled_at not refreshed (age {age}s)"
        # ts advanced -> _sync_one completed the full path
        assert after["last_clients_ts"] == 2000
        assert after["last_error"] == ""

    def test_aware_last_polled_at_still_works(self, mod, monkeypatch):
        aware_old = datetime.now(timezone.utc) - timedelta(minutes=5)
        _seed(mod, aware_old)
        calls = _patch_caffesta(mod, monkeypatch, clients_ts=3000)
        with _Capture() as cap:
            _run(mod["ls"].run_loyalty_sync_job())
        log = cap.text()
        assert NAIVE_ERR not in log
        assert "outer catch" not in log, log
        assert calls["get_updates"] >= 1
        assert _get_cfg(mod)["last_clients_ts"] == 3000

    def test_naive_recent_poll_is_throttled(self, mod, monkeypatch):
        """Interval logic must still skip when the last poll was just now."""
        naive_now = datetime.utcnow()
        _seed(mod, naive_now, interval=10)
        calls = _patch_caffesta(mod, monkeypatch, clients_ts=4000)
        with _Capture() as cap:
            _run(mod["ls"].run_loyalty_sync_job())
        log = cap.text()
        assert NAIVE_ERR not in log
        assert calls["get_updates"] == 0, "should have been throttled by sync_interval_min"
        assert _get_cfg(mod)["last_clients_ts"] == 1000, "ts must be untouched when skipped"

    def test_naive_last_synced_at_fallback(self, mod, monkeypatch):
        """No last_polled_at → falls back to last_synced_at (also naive)."""
        _seed(mod, None, last_synced_at=datetime.utcnow() - timedelta(minutes=30))
        calls = _patch_caffesta(mod, monkeypatch, clients_ts=5000)
        with _Capture() as cap:
            _run(mod["ls"].run_loyalty_sync_job())
        log = cap.text()
        assert NAIVE_ERR not in log, log
        assert "outer catch" not in log, log
        assert calls["get_updates"] >= 1
        assert _get_cfg(mod)["last_clients_ts"] == 5000

    def test_client_processing_with_naive_state(self, mod, monkeypatch):
        """End-to-end: naive state + a returned client → upsert into loyalty_clients."""
        db = mod["db"]
        phone = "375990000001"
        _run(db.loyalty_clients.delete_many({"restaurant_id": RID, "phone_norm": phone}))
        _seed(mod, datetime.utcnow() - timedelta(minutes=9))
        _patch_caffesta(mod, monkeypatch, clients_ts=6000, client_list=[
            {"normPhone": phone, "bonusBalance": 12.5, "pointBalance": 3,
             "name": "TEST", "lastName": "Client", "uuid": "TEST_uuid"},
        ])
        with _Capture() as cap:
            _run(mod["ls"].run_loyalty_sync_job())
        assert NAIVE_ERR not in cap.text()
        cli = _run(db.loyalty_clients.find_one(
            {"restaurant_id": RID, "phone_norm": phone}, {"_id": 0}))
        assert cli is not None, "client was not upserted"
        assert cli["last_bonus_balance"] == 12.5
        _run(db.loyalty_clients.delete_many({"restaurant_id": RID, "phone_norm": phone}))

    def test_disabled_config_is_ignored(self, mod, monkeypatch):
        _seed(mod, datetime.utcnow() - timedelta(minutes=30), enabled=False)
        calls = _patch_caffesta(mod, monkeypatch, clients_ts=7000)
        with _Capture() as cap:
            _run(mod["ls"].run_loyalty_sync_job())
        assert NAIVE_ERR not in cap.text()
        assert calls["get_updates"] == 0


class TestSyncNowEndpoint:
    """POST /sync-now must work regardless of last_polled_at tzinfo.
    Real Caffesta creds are absent → we accept a get_updates error, but the
    endpoint must return 200 and refresh last_polled_at."""

    @pytest.mark.parametrize("naive", [True, False])
    def test_sync_now_updates_polled_at(self, mod, http, naive):
        last = (datetime.utcnow() if naive else datetime.now(timezone.utc)) - timedelta(minutes=5)
        _seed(mod, last)
        r = http.post(f"{BASE_URL}/api/restaurants/{RID}/loyalty/sync-now", timeout=60)
        assert r.status_code == 200, r.text[:400]
        body = r.json()
        assert "ok" in body and "error" in body and "info" in body
        assert NAIVE_ERR not in (body.get("error") or "")
        after = _get_cfg(mod)
        polled = after["last_polled_at"]
        polled_aware = polled if polled.tzinfo else polled.replace(tzinfo=timezone.utc)
        assert (datetime.now(timezone.utc) - polled_aware).total_seconds() < 90

    def test_config_endpoint_ok(self, mod, http):
        r = http.get(f"{BASE_URL}/api/restaurants/{RID}/loyalty/config", timeout=30)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert "_id" not in data
        assert data["restaurant_id"] == RID
        assert isinstance(data["sync_interval_min"], int)


class TestIter30Regression:
    """Category is_active toggle regression (iteration 30)."""

    def test_toggle_category_active(self, http):
        r = http.get(f"{BASE_URL}/api/restaurants/{RID}/categories", timeout=30)
        assert r.status_code == 200, r.text[:300]
        cats = r.json()
        assert isinstance(cats, list) and cats
        for c in cats:
            assert "_id" not in c
        target = next((c for c in cats if c["id"] == CAT_ID), cats[0])
        cid = target["id"]
        original = bool(target.get("is_active", True))
        try:
            r = http.put(f"{BASE_URL}/api/restaurants/{RID}/categories/{cid}",
                         json={"is_active": not original}, timeout=30)
            assert r.status_code == 200, r.text[:300]
            cats2 = http.get(f"{BASE_URL}/api/restaurants/{RID}/categories", timeout=30).json()
            got = next(c for c in cats2 if c["id"] == cid)
            assert bool(got["is_active"]) == (not original), "is_active toggle not persisted"
        finally:
            http.put(f"{BASE_URL}/api/restaurants/{RID}/categories/{cid}",
                     json={"is_active": original}, timeout=30)
            cats3 = http.get(f"{BASE_URL}/api/restaurants/{RID}/categories", timeout=30).json()
            restored = next(c for c in cats3 if c["id"] == cid)
            assert bool(restored["is_active"]) == original
