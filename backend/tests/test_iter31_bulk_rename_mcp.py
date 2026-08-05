"""
Iteration 31 — bugfix verification: MCP tool `bulk_rename_categories` payload shape.

The MCP tool now converts mapping={cat_id: new_name} into a top-level JSON array
[{"id": ..., "name": ...}] which is what POST /categories/bulk-rename expects.

Covers:
* Backend: POST /api/restaurants/{rid}/categories/bulk-rename with a bare array
* MCP: bulk_rename_categories tool end-to-end (2 categories) via fastmcp in-memory Client
* Persistence check via GET /categories + restore of original names
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
CAT_ID = "768fe425-3b91-40c4-9df9-0090f2b3ed06"  # Завтраки до 16.00
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


def _categories(client):
    r = client.get(f"{BASE_URL}/api/restaurants/{RID}/categories", timeout=30)
    assert r.status_code == 200, r.text[:300]
    cats = r.json()
    assert isinstance(cats, list) and cats
    for c in cats:
        assert "_id" not in c, "MongoDB _id leaked in response"
    return cats


def _name_of(client, cat_id):
    match = [c for c in _categories(client) if c["id"] == cat_id]
    assert match, f"category {cat_id} not found"
    return match[0]["name"]


@pytest.fixture(scope="module")
def targets(client):
    """Two real categories to rename: the known test category + one more."""
    cats = _categories(client)
    ids = [c["id"] for c in cats]
    assert CAT_ID in ids, f"{CAT_ID} missing"
    second = next(c for c in cats if c["id"] != CAT_ID)
    first = next(c for c in cats if c["id"] == CAT_ID)
    return {first["id"]: first["name"], second["id"]: second["name"]}


@pytest.fixture(scope="module", autouse=True)
def restore_names(client, targets):
    """MANDATORY: restore original category names after the module."""
    yield
    payload = [{"id": cid, "name": name} for cid, name in targets.items()]
    r = client.post(
        f"{BASE_URL}/api/restaurants/{RID}/categories/bulk-rename",
        json=payload,
        timeout=60,
    )
    assert r.status_code == 200, f"restore failed: {r.status_code} {r.text[:300]}"
    for cid, name in targets.items():
        assert _name_of(client, cid) == name, f"restore mismatch for {cid}"


# ─── MCP in-process driver ──────────────────────────────────────────────────

def _run_mcp(coro_factory):
    sys.path.insert(0, "/app/mcp_server")
    os.environ["REST_MENU_API_URL"] = BASE_URL
    os.environ["REST_MENU_USERNAME"] = USERNAME
    os.environ["REST_MENU_PASSWORD"] = PASSWORD
    from restmenu_mcp import server as mcp_server

    mcp_server.API_URL = BASE_URL
    mcp_server.USERNAME = USERNAME
    mcp_server.PASSWORD = PASSWORD
    mcp_server.session.token = None
    from fastmcp import Client

    async def main():
        async with Client(mcp_server.mcp) as c:
            return await coro_factory(c)

    return asyncio.run(main())


class TestBackendBulkRenameContract:
    def test_bare_array_body_accepted(self, client, targets):
        cid = CAT_ID
        original = targets[cid]
        payload = [{"id": cid, "name": f"TEST_{original}"}]
        r = client.post(
            f"{BASE_URL}/api/restaurants/{RID}/categories/bulk-rename",
            json=payload,
            timeout=60,
        )
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data == {"updated": 1, "skipped": 0}, data
        assert _name_of(client, cid) == f"TEST_{original}"

        # revert this one immediately
        client.post(
            f"{BASE_URL}/api/restaurants/{RID}/categories/bulk-rename",
            json=[{"id": cid, "name": original}],
            timeout=60,
        )
        assert _name_of(client, cid) == original

    def test_wrapped_object_body_rejected(self, client):
        """Old (buggy) MCP payload shape must still be a 422 — documents the contract."""
        r = client.post(
            f"{BASE_URL}/api/restaurants/{RID}/categories/bulk-rename",
            json={"renames": {CAT_ID: "X"}},
            timeout=30,
        )
        assert r.status_code == 422, f"expected 422, got {r.status_code}: {r.text[:300]}"

    def test_invalid_entries_are_skipped(self, client):
        r = client.post(
            f"{BASE_URL}/api/restaurants/{RID}/categories/bulk-rename",
            json=[{"id": "does-not-exist", "name": "Nope"}, {"id": CAT_ID, "name": "   "}],
            timeout=60,
        )
        assert r.status_code == 200, r.text[:300]
        assert r.json() == {"updated": 0, "skipped": 2}, r.json()


class TestMcpBulkRenameTool:
    def test_mcp_source_sends_bare_array(self):
        src = open("/app/mcp_server/restmenu_mcp/server.py", encoding="utf-8").read()
        assert '"renames": mapping' not in src
        assert 'json_body=renames' in src

    def test_mcp_bulk_rename_two_categories(self, client, targets):
        ids = list(targets.keys())
        new_names = {cid: f"TEST_MCP_{i}" for i, cid in enumerate(ids)}

        async def flow(c):
            await c.call_tool("select_restaurant", {"id_or_name": RID})
            r = await c.call_tool("bulk_rename_categories", {"mapping": new_names})
            return r.data

        data = _run_mcp(flow)
        assert data == {"updated": 2, "skipped": 0}, data

        # persistence via REST GET
        for cid, expected in new_names.items():
            assert _name_of(client, cid) == expected, f"{cid} not renamed"

        # restore originals through the MCP tool as well
        async def restore(c):
            await c.call_tool("select_restaurant", {"id_or_name": RID})
            r = await c.call_tool("bulk_rename_categories", {"mapping": targets})
            return r.data

        rdata = _run_mcp(restore)
        assert rdata == {"updated": 2, "skipped": 0}, rdata
        for cid, original in targets.items():
            assert _name_of(client, cid) == original
