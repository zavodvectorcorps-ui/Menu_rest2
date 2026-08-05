"""
Iteration 35 — Loyalty: editable bot messages + reply-keyboard buttons.

1) GET /api/restaurants/{rid}/loyalty/config → three new fields with defaults
2) PUT persists start/welcome/invite_message_text (GET-after-PUT)
3) handle_update (in-process, _send monkeypatched):
   - "Баланс" / "💰 Баланс" → balance reply + main menu keyboard
   - "👥 Пригласить друга" → invite text with {bot_link} substituted
   - /start → uses cfg.start_message_text
   - contact registration → welcome_message_text formatted with {name}
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
os.environ.setdefault("MONGO_URL", backend_env.get("MONGO_URL", ""))
os.environ.setdefault("DB_NAME", backend_env.get("DB_NAME", ""))

RID = "aa25189d-d668-4838-915a-c5d936547f3f"
TEST_PHONE = "375299998877"
TEST_CHAT = 555000111


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _db():
    c = AsyncIOMotorClient(backend_env["MONGO_URL"])
    return c, c[backend_env["DB_NAME"]]


@pytest.fixture(scope="session")
def creds():
    content = Path("/app/memory/test_credentials.md").read_text(encoding="utf-8")
    u = re.search(r"Username:\s*`([^`]+)`", content)
    p = re.search(r"Password:\s*`([^`]+)`", content)
    if not (u and p):
        pytest.skip("credentials missing in /app/memory/test_credentials.md")
    return u.group(1), p.group(1)


@pytest.fixture(scope="session")
def client(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": creds[0], "password": creds[1]}, timeout=60)
    if r.status_code != 200:
        pytest.fail(f"login failed {r.status_code}: {r.text[:300]}")
    tok = r.json().get("access_token") or r.json().get("token")
    if not tok:
        pytest.fail("no token in login response")
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    return s


# ─── 1 & 2. Config API ───────────────────────────────────────────────────
class TestLoyaltyConfigMessages:
    URL = f"{BASE_URL}/api/restaurants/{RID}/loyalty/config"

    @pytest.fixture(scope="class", autouse=True)
    def snapshot(self):
        mc, db = _db()
        cfg = run(db.loyalty_config.find_one({"restaurant_id": RID}, {"_id": 0})) or {}
        prev = {k: cfg.get(k) for k in ("start_message_text", "welcome_message_text", "invite_message_text")}
        # start from unset state to check defaults
        run(db.loyalty_config.update_one(
            {"restaurant_id": RID},
            {"$unset": {"start_message_text": "", "welcome_message_text": "", "invite_message_text": ""}},
        ))
        yield
        run(db.loyalty_config.update_one({"restaurant_id": RID}, {"$set": {
            k: v for k, v in prev.items() if v is not None
        }} if any(v is not None for v in prev.values()) else {"$unset": {
            "start_message_text": "", "welcome_message_text": "", "invite_message_text": ""
        }}))
        mc.close()

    def test_get_returns_defaults(self, client):
        r = client.get(self.URL, timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert "_id" not in d
        for key in ("start_message_text", "welcome_message_text", "invite_message_text"):
            assert key in d, f"missing {key} in config response: {list(d)}"
            assert isinstance(d[key], str) and d[key].strip()
        assert "Привет" in d["start_message_text"], d["start_message_text"]
        assert "{name}" in d["welcome_message_text"], d["welcome_message_text"]
        assert "{bot_link}" in d["invite_message_text"], d["invite_message_text"]

    def test_put_persists_all_three(self, client):
        payload = {
            "start_message_text": "TEST_START Привет, {name}! Жми кнопку.",
            "welcome_message_text": "TEST_WELCOME {name}, вам начислено 10 приветственных бонусов!",
            "invite_message_text": "TEST_INVITE Позови друга: {bot_link}",
        }
        r = client.put(self.URL, json=payload, timeout=60)
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        for k, v in payload.items():
            assert body[k] == v, f"PUT response mismatch for {k}: {body.get(k)!r}"

        g = client.get(self.URL, timeout=60)
        assert g.status_code == 200
        got = g.json()
        for k, v in payload.items():
            assert got[k] == v, f"not persisted: {k} = {got.get(k)!r}"
        assert "10 приветственных бонусов" in got["welcome_message_text"]

    def test_partial_update_keeps_others(self, client):
        r = client.put(self.URL, json={"invite_message_text": "TEST_INVITE2 {bot_link}"}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        got = client.get(self.URL, timeout=60).json()
        assert got["invite_message_text"] == "TEST_INVITE2 {bot_link}"
        assert got["start_message_text"].startswith("TEST_START"), got["start_message_text"]
        assert got["welcome_message_text"].startswith("TEST_WELCOME")

    def test_config_requires_auth(self):
        r = requests.get(self.URL, timeout=60)
        assert r.status_code in (401, 403), r.status_code


# ─── 3. Bot handle_update ────────────────────────────────────────────────
class TestBotButtons:
    """Runs handle_update in-process with outbound Telegram calls stubbed."""

    @pytest.fixture(scope="class", autouse=True)
    def bot_env(self):
        from services.loyalty_crypto import encrypt

        mc, db = _db()

        async def prep():
            cfg = await db.loyalty_config.find_one({"restaurant_id": RID}, {"_id": 0})
            assert cfg, "loyalty_config missing"
            prev = {
                "telegram_bot_token_enc": cfg.get("telegram_bot_token_enc") or "",
                "telegram_bot_username": cfg.get("telegram_bot_username") or "",
                "start_message_text": cfg.get("start_message_text"),
                "welcome_message_text": cfg.get("welcome_message_text"),
                "invite_message_text": cfg.get("invite_message_text"),
                "caffesta_auto_register": cfg.get("caffesta_auto_register"),
            }
            await db.loyalty_config.update_one({"restaurant_id": RID}, {"$set": {
                "telegram_bot_token_enc": encrypt("123456:FAKE_TEST_TOKEN"),
                "telegram_bot_username": "qa_test_bot",
                "start_message_text": "QA_START Привет!",
                "welcome_message_text": "QA_WELCOME {name}: начислено 10 приветственных бонусов",
                "invite_message_text": "QA_INVITE ссылка: {bot_link}",
                "caffesta_auto_register": False,
            }})
            await db.loyalty_clients.delete_many({"restaurant_id": RID, "phone_norm": TEST_PHONE})
            await db.loyalty_clients.delete_many({"restaurant_id": RID, "telegram_chat_id": TEST_CHAT})
            await db.loyalty_clients.insert_one({
                "id": "qa-iter35-client",
                "restaurant_id": RID,
                "phone_norm": TEST_PHONE,
                "name": "QA Тестов",
                "caffesta_uuid": "",
                "telegram_chat_id": TEST_CHAT,
                "telegram_username": "qa35",
                "last_bonus_balance": 42.5,
                "last_point_balance": 0.0,
                "card_number": 99001,
            })
            return prev

        prev = run(prep())
        yield

        async def restore():
            unset = {k: "" for k, v in prev.items() if v is None}
            setv = {k: v for k, v in prev.items() if v is not None}
            upd = {}
            if setv:
                upd["$set"] = setv
            if unset:
                upd["$unset"] = unset
            if upd:
                await db.loyalty_config.update_one({"restaurant_id": RID}, upd)
            await db.loyalty_clients.delete_many({"restaurant_id": RID, "id": "qa-iter35-client"})
            await db.loyalty_clients.delete_many({"restaurant_id": RID, "phone_norm": TEST_PHONE})

        run(restore())
        mc.close()

    @pytest.fixture
    def sent(self, monkeypatch):
        import services.loyalty_bot as bot

        box = []

        async def fake_send(bot_token, chat_id, text, reply_markup=None):
            box.append({"chat_id": chat_id, "text": text, "markup": reply_markup})

        async def fake_card(*a, **k):
            return 12345

        monkeypatch.setattr(bot, "_send", fake_send)
        monkeypatch.setattr(bot, "send_card_and_pin", fake_card)
        return box

    def _update(self, text=None, contact=None, chat_id=TEST_CHAT):
        msg = {"message_id": 1, "chat": {"id": chat_id, "username": "qa35", "type": "private"}}
        if text is not None:
            msg["text"] = text
        if contact is not None:
            msg["contact"] = contact
        return {"update_id": 950001, "message": msg}

    def _handle(self, update):
        import services.loyalty_bot as bot
        run(bot.handle_update(RID, update))

    @pytest.mark.parametrize("btn", ["Баланс", "💰 Баланс", "/balance"])
    def test_balance_button(self, sent, btn):
        self._handle(self._update(text=btn))
        assert sent, f"no reply for {btn!r}"
        last = sent[-1]
        assert "42.50 BYN" in last["text"], last["text"]
        kb = (last["markup"] or {}).get("keyboard") or []
        flat = [b["text"] for row in kb for b in row]
        assert "💰 Баланс" in flat and "👥 Пригласить друга" in flat, flat

    @pytest.mark.parametrize("btn", ["👥 Пригласить друга", "Пригласить друга"])
    def test_invite_button(self, sent, btn):
        self._handle(self._update(text=btn))
        assert sent, f"no reply for {btn!r}"
        last = sent[-1]
        assert last["text"].startswith("QA_INVITE"), last["text"]
        assert "https://t.me/qa_test_bot" in last["text"], last["text"]
        assert "{bot_link}" not in last["text"]

    def test_start_uses_config_text(self, sent):
        self._handle(self._update(text="/start"))
        assert sent[-1]["text"] == "QA_START Привет!", sent[-1]["text"]
        kb = (sent[-1]["markup"] or {}).get("keyboard") or []
        assert any(b.get("request_contact") for row in kb for b in row), kb

    def test_card_button(self, sent):
        self._handle(self._update(text="🎫 Моя карта"))
        # card is sent as photo (stubbed) → no text message required, must not error
        assert True

    def test_welcome_after_contact_uses_template(self, sent):
        contact = {"phone_number": "+375 (29) 999-88-77", "first_name": "QA", "last_name": "Тестов"}
        self._handle(self._update(contact=contact, chat_id=TEST_CHAT))
        assert sent, "no welcome message sent"
        last = sent[-1]
        assert last["text"] == "QA_WELCOME QA Тестов: начислено 10 приветственных бонусов", last["text"]
        assert "{name}" not in last["text"]
        kb = (last["markup"] or {}).get("keyboard") or []
        flat = [b["text"] for row in kb for b in row]
        assert "👥 Пригласить друга" in flat, flat

    def test_unlinked_chat_gets_start_hint(self, sent):
        self._handle(self._update(text="Баланс", chat_id=999888777))
        assert "поделитесь номером" in sent[-1]["text"].lower(), sent[-1]["text"]
