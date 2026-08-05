"""
Iteration 34 — Loyalty module tests:
1) GET /api/restaurants/{rid}/loyalty/clients returns birthday & sex fields
2) Telegram webhook new-contact registration no longer replies "карта не найдена"
3) Bot /birthday and /gender dialogs update DB
"""

import asyncio
import os
import re
import sys
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, "/app/backend")

frontend_env = dotenv_values("/app/frontend/.env")
backend_env = dotenv_values("/app/backend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or frontend_env["REACT_APP_BACKEND_URL"]).rstrip("/")
os.environ.setdefault("LOYALTY_ENCRYPTION_KEY", backend_env.get("LOYALTY_ENCRYPTION_KEY", ""))
RID = "aa25189d-d668-4838-915a-c5d936547f3f"
NEW_PHONE = "375291234567"


def _db():
    client = AsyncIOMotorClient(backend_env["MONGO_URL"])
    return client, client[backend_env["DB_NAME"]]


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.get_event_loop_policy()


@pytest.fixture(scope="session")
def creds():
    content = Path("/app/memory/test_credentials.md").read_text(encoding="utf-8")
    u = re.search(r"Username:\s*`([^`]+)`", content)
    p = re.search(r"Password:\s*`([^`]+)`", content)
    assert u and p, "credentials not found"
    return u.group(1), p.group(1)


@pytest.fixture(scope="session")
def token(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": creds[0], "password": creds[1]}, timeout=60)
    assert r.status_code == 200, f"login failed {r.status_code}: {r.text[:300]}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    assert tok, f"no token in login response: {data}"
    return tok


@pytest.fixture(scope="session")
def client(token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return s


# ─── 1. Clients endpoint returns birthday/sex ────────────────────────────
class TestClientsEndpoint:
    def test_clients_contain_birthday_and_sex(self, client):
        r = client.get(f"{BASE_URL}/api/restaurants/{RID}/loyalty/clients", timeout=60)
        assert r.status_code == 200, r.text[:300]
        docs = r.json()
        assert isinstance(docs, list)
        by_name = {d["name"]: d for d in docs}
        for expected in ("Иван Иванов", "Мария Петрова", "Без данных"):
            assert expected in by_name, f"missing seeded client {expected}; got {list(by_name)}"

        ivan = by_name["Иван Иванов"]
        assert ivan["birthday"] == "1990-03-15"
        assert ivan["sex"] == "M"
        assert ivan["card_number"] == "00001"

        maria = by_name["Мария Петрова"]
        assert maria["birthday"] == "1985-07-22"
        assert maria["sex"] == "F"

        empty = by_name["Без данных"]
        assert empty.get("birthday") is None
        assert empty.get("sex") is None

        # no mongo _id leakage
        for d in docs:
            assert "_id" not in d
            for key in ("id", "phone_norm", "restaurant_id", "last_bonus_balance"):
                assert key in d, f"missing key {key} in {d}"

    def test_clients_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/restaurants/{RID}/loyalty/clients", timeout=60)
        assert r.status_code in (401, 403), r.status_code


# ─── 2. Webhook: new contact registration ────────────────────────────────
class TestWebhookNewContact:
    @pytest.fixture(scope="class", autouse=True)
    def bot_token_setup(self):
        """Temporarily install a fake (encrypted) bot token so handle_update proceeds."""
        from services.loyalty_crypto import encrypt

        mc, db = _db()

        async def setup():
            cfg = await db.loyalty_config.find_one({"restaurant_id": RID}, {"_id": 0})
            assert cfg, "loyalty_config missing for test restaurant"
            prev = cfg.get("telegram_bot_token_enc") or ""
            await db.loyalty_config.update_one(
                {"restaurant_id": RID},
                {"$set": {"telegram_bot_token_enc": encrypt("123456:FAKE_TEST_TOKEN")}},
            )
            return cfg["webhook_secret"], prev

        secret, prev = run(setup())

        async def cleanup():
            await db.loyalty_config.update_one(
                {"restaurant_id": RID}, {"$set": {"telegram_bot_token_enc": prev}}
            )
            await db.loyalty_clients.delete_many({"restaurant_id": RID, "phone_norm": NEW_PHONE})

        run(db.loyalty_clients.delete_many({"restaurant_id": RID, "phone_norm": NEW_PHONE}))
        self.__class__.secret = secret
        yield secret
        run(cleanup())
        mc.close()

    def test_new_contact_creates_client_with_card(self):
        secret = self.__class__.secret
        update = {
            "update_id": 900001,
            "message": {
                "message_id": 1,
                "chat": {"id": 987654321, "username": "qa_new_user", "type": "private"},
                "contact": {
                    "phone_number": "+375 (29) 123-45-67",
                    "first_name": "Тест",
                    "last_name": "Новый",
                },
            },
        }
        r = requests.post(
            f"{BASE_URL}/api/loyalty/webhook/{RID}/{secret}", json=update, timeout=120
        )
        assert r.status_code == 200, r.text[:300]
        assert r.json().get("ok") is True

        mc, db = _db()
        doc = run(db.loyalty_clients.find_one({"restaurant_id": RID, "phone_norm": NEW_PHONE}, {"_id": 0}))
        mc.close()
        assert doc, "new loyalty client was not inserted by webhook contact branch"
        assert doc["telegram_chat_id"] == 987654321
        assert doc["telegram_username"] == "qa_new_user"
        assert doc["name"] == "Тест Новый"
        assert doc.get("card_number"), "card_number was not auto-assigned"
        assert doc.get("pending_prompt") in (None, ""), doc.get("pending_prompt")

    def test_no_card_not_found_branch_in_source(self):
        # Ignore comments — only real code lines matter.
        lines = [
            ln for ln in Path("/app/backend/services/loyalty_bot.py").read_text(encoding="utf-8").splitlines()
            if not ln.strip().startswith("#")
        ]
        src = "\n".join(lines)
        for bad in ("не нашли карту", "карта не найдена", "не найдена карта"):
            assert bad not in src, f"bot source still sends user-facing text: {bad}"

    def test_backend_log_has_no_not_found_message(self):
        log = ""
        for p in ("/var/log/supervisor/backend.err.log", "/var/log/supervisor/backend.out.log"):
            try:
                log += Path(p).read_text(encoding="utf-8", errors="ignore")[-200000:]
            except FileNotFoundError:
                pass
        assert "не нашли карту" not in log
        assert "карта не найдена" not in log


# ─── 3. /birthday and /gender bot dialogs ────────────────────────────────
class TestBirthdayGenderCommands:
    CHAT_ID = 333  # seeded client "Без данных"

    @pytest.fixture(scope="class", autouse=True)
    def setup(self):
        from services.loyalty_crypto import encrypt

        mc, db = _db()

        async def prep():
            cfg = await db.loyalty_config.find_one({"restaurant_id": RID}, {"_id": 0})
            prev = cfg.get("telegram_bot_token_enc") or ""
            await db.loyalty_config.update_one(
                {"restaurant_id": RID},
                {"$set": {"telegram_bot_token_enc": encrypt("123456:FAKE_TEST_TOKEN")}},
            )
            return cfg["webhook_secret"], prev

        secret, prev = run(prep())
        self.__class__.secret = secret
        yield

        async def restore():
            await db.loyalty_config.update_one(
                {"restaurant_id": RID}, {"$set": {"telegram_bot_token_enc": prev}}
            )
            # restore seeded state for "Без данных"
            await db.loyalty_clients.update_one(
                {"restaurant_id": RID, "telegram_chat_id": self.CHAT_ID},
                {"$set": {"birthday": None, "sex": None, "pending_prompt": None}},
            )

        run(restore())
        mc.close()

    def _send(self, text):
        update = {
            "update_id": 900100,
            "message": {
                "message_id": 2,
                "chat": {"id": self.CHAT_ID, "username": "qa_bd", "type": "private"},
                "text": text,
            },
        }
        r = requests.post(
            f"{BASE_URL}/api/loyalty/webhook/{RID}/{self.__class__.secret}", json=update, timeout=120
        )
        assert r.status_code == 200, r.text[:300]
        return r

    def _doc(self):
        mc, db = _db()
        d = run(db.loyalty_clients.find_one({"restaurant_id": RID, "telegram_chat_id": self.CHAT_ID}, {"_id": 0}))
        mc.close()
        return d

    def test_birthday_flow(self):
        self._send("/birthday")
        assert self._doc().get("pending_prompt") == "birthday"
        self._send("15.03.1990")
        d = self._doc()
        assert d.get("birthday") == "1990-03-15", d.get("birthday")
        assert d.get("pending_prompt") is None

    def test_gender_flow(self):
        self._send("/gender")
        assert self._doc().get("pending_prompt") == "gender"
        self._send("М")
        d = self._doc()
        assert d.get("sex") == "M", d.get("sex")
        assert d.get("pending_prompt") is None

    def test_invalid_birthday_keeps_prompt(self):
        self._send("/birthday")
        self._send("not-a-date")
        d = self._doc()
        assert d.get("pending_prompt") == "birthday", "invalid input should keep pending prompt"
