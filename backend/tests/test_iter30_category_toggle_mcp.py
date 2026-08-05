"""
Iteration 30 — bugfix verification: MCP `update_category` field name (is_active, not is_visible).

Covers:
* Backend: PUT /api/restaurants/{rid}/categories/{cid} with is_active false/true
* Backend: PUT with wrong field is_visible → silently ignored (documents the bug)
* Backend: PUT name only → is_active untouched
* MCP: update_category tool via fastmcp in-memory Client
"""

import asyncio
import os
import sys

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")

RID = "aa25189d-d668-4838-915a-c5d936547f3f"
CAT_ID = "768fe425-3b91-40c4-9df9-0090f2b3ed06"
USERNAME = "admin"
PASSWORD = "220066"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"username": USERNAME, "password": PASSWORD}, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"login failed {r.status_code}: {r.text[:300]}")
    token = r.json().get("access_token") or r.json().get("token")
    assert token, f"no token in {r.json()}"
    s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return s


def _cat_from_list(client, cat_id=CAT_ID):
    r = client.get(f"{BASE_URL}/api/restaurants/{RID}/categories", timeout=30)
    assert r.status_code == 200, r.text[:300]
    cats = r.json()
    assert isinstance(cats, list) and cats
    for c in cats:
        assert "_id" not in c
    match = [c for c in cats if c["id"] == cat_id]
    assert match, f"category {cat_id} not found"
    return match[0]


@pytest.fixture(scope="module", autouse=True)
def restore_category(client):
    yield
    client.put(
        f"{BASE_URL}/api/restaurants/{RID}/categories/{CAT_ID}",
        json={"is_active": True, "name": "Завтраки до 16.00"},
        timeout=30,
    )
    final = _cat_from_list(client)
    assert final["is_active"] is True
    assert final["name"] == "Завтраки до 16.00"


class TestCategoryActiveToggle:
    def test_precondition_category_exists(self, client):
        cat = _cat_from_list(client)
        assert cat["name"] == "Завтраки до 16.00"
        assert isinstance(cat["is_active"], bool)

    def test_disable_with_is_active_false(self, client):
        r = client.put(
            f"{BASE_URL}/api/restaurants/{RID}/categories/{CAT_ID}",
            json={"is_active": False},
            timeout=30,
        )
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        assert body["is_active"] is False, f"response still active: {body.get('is_active')}"
        assert "_id" not in body
        # persistence via GET list
        assert _cat_from_list(client)["is_active"] is False

    def test_is_visible_field_is_ignored(self, client):
        """Wrong field name must NOT flip is_active (extra=ignore). Currently is_active=False."""
        r = client.put(
            f"{BASE_URL}/api/restaurants/{RID}/categories/{CAT_ID}",
            json={"is_visible": True},
            timeout=30,
        )
        assert r.status_code == 200, r.text[:300]
        assert r.json()["is_active"] is False
        assert _cat_from_list(client)["is_active"] is False

    def test_enable_with_is_active_true(self, client):
        r = client.put(
            f"{BASE_URL}/api/restaurants/{RID}/categories/{CAT_ID}",
            json={"is_active": True},
            timeout=30,
        )
        assert r.status_code == 200, r.text[:300]
        assert r.json()["is_active"] is True
        assert _cat_from_list(client)["is_active"] is True

    def test_rename_does_not_touch_is_active(self, client):
        r = client.put(
            f"{BASE_URL}/api/restaurants/{RID}/categories/{CAT_ID}",
            json={"name": "TEST_Завтраки до 16.00"},
            timeout=30,
        )
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        assert body["name"] == "TEST_Завтраки до 16.00"
        assert body["is_active"] is True
        cat = _cat_from_list(client)
        assert cat["name"] == "TEST_Завтраки до 16.00"
        assert cat["is_active"] is True
        # restore name
        client.put(
            f"{BASE_URL}/api/restaurants/{RID}/categories/{CAT_ID}",
            json={"name": "Завтраки до 16.00"},
            timeout=30,
        )

    def test_update_unknown_category_returns_404(self, client):
        r = client.put(
            f"{BASE_URL}/api/restaurants/{RID}/categories/does-not-exist",
            json={"is_active": False},
            timeout=30,
        )
        assert r.status_code == 404, f"expected 404, got {r.status_code}: {r.text[:200]}"


# ── MCP tool level tests ───────────────────────────────────────────────────

def _run_mcp(coro_factory):
    sys.path.insert(0, "/app/mcp_server")
    os.environ["REST_MENU_API_URL"] = BASE_URL
    os.environ["REST_MENU_USERNAME"] = USERNAME
    os.environ["REST_MENU_PASSWORD"] = PASSWORD
    from restmenu_mcp import server as mcp_server  # noqa: WPS433
    mcp_server.API_URL = BASE_URL
    mcp_server.USERNAME = USERNAME
    mcp_server.PASSWORD = PASSWORD
    mcp_server.session.token = None
    from fastmcp import Client

    async def main():
        async with Client(mcp_server.mcp) as c:
            return await coro_factory(c)

    return asyncio.run(main())


class TestMcpUpdateCategory:
    def test_docstring_mentions_is_active_not_is_visible(self):
        src = open("/app/mcp_server/restmenu_mcp/server.py", encoding="utf-8").read()
        assert "is_visible" not in src, "is_visible still present in MCP server source"
        assert "is_active" in src

    def test_mcp_update_category_disables_and_enables(self, client):
        async def flow(c):
            out = {}
            await c.call_tool("select_restaurant", {"id_or_name": RID})
            r1 = await c.call_tool("update_category", {"category_id": CAT_ID, "updates": {"is_active": False}})
            out["off"] = r1.data
            r2 = await c.call_tool("list_categories", {})
            out["list_off"] = [x for x in r2.data if x["id"] == CAT_ID][0]
            r3 = await c.call_tool("update_category", {"category_id": CAT_ID, "updates": {"is_active": True}})
            out["on"] = r3.data
            return out

        res = _run_mcp(flow)
        assert res["off"]["is_active"] is False, res["off"]
        assert res["list_off"]["is_active"] is False
        assert res["on"]["is_active"] is True
        assert _cat_from_list(client)["is_active"] is True

    def test_mcp_bulk_rename_categories_tool(self):
        """MCP bulk_rename sends {'renames': mapping} but API expects a list body."""
        async def flow(c):
            await c.call_tool("select_restaurant", {"id_or_name": RID})
            try:
                r = await c.call_tool("bulk_rename_categories", {"mapping": {CAT_ID: "Завтраки до 16.00"}})
                return {"ok": True, "data": r.data}
            except Exception as exc:  # noqa: BLE001
                return {"ok": False, "error": str(exc)}

        res = _run_mcp(flow)
        assert res["ok"], f"bulk_rename_categories MCP tool failed: {res.get('error')}"
        assert res["data"].get("updated") == 1, res["data"]
