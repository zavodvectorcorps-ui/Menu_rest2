"""Iteration 21: local sub-products CRUD + AI recipe parser endpoint + cost-catalog
includes local subproducts even when Caffesta is not configured (preview env).
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # frontend/.env is the source of truth in this env.
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                break

API = f"{BASE_URL}/api"


# ---------- Fixtures ----------

@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def auth(session):
    r = session.post(f"{API}/auth/login", json={"username": "admin", "password": "220066"})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("access_token") or data.get("token")
    assert token, f"no token in login response: {data}"
    restaurants = data.get("restaurants") or data.get("user", {}).get("restaurants") or []
    assert restaurants, f"no restaurants in login response: {data}"
    rid = restaurants[0].get("id") or restaurants[0]
    session.headers.update({"Authorization": f"Bearer {token}"})
    return {"token": token, "rid": rid}


@pytest.fixture(scope="module")
def created_ids():
    return []


# ---------- Local sub-products CRUD ----------

class TestLocalSubproductsCRUD:
    def test_list_initially_returns_data_field(self, session, auth):
        r = session.get(f"{API}/restaurants/{auth['rid']}/local-subproducts")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "data" in body and "total" in body
        assert isinstance(body["data"], list)

    def test_create_local_subproduct(self, session, auth, created_ids):
        payload = {
            "name": "TEST_Соус кукуруза",
            "yield_g": 1000,
            "ingredients": [
                {"name": "Соль", "qty": 10, "unit": "г", "unit_factor": 0.001, "unit_cost": 50.0},
                {"name": "Сахар", "qty": 100, "unit": "г", "unit_factor": 0.001, "unit_cost": 80.0},
            ],
            "notes": "TEST iter21",
        }
        r = session.post(f"{API}/restaurants/{auth['rid']}/local-subproducts", json=payload)
        assert r.status_code == 200, r.text
        doc = r.json()
        # required shape
        for key in ("id", "name", "yield_g", "ingredients", "total_cost", "cost_per_kg"):
            assert key in doc, f"missing key {key}"
        assert doc["name"] == "TEST_Соус кукуруза"
        assert doc["yield_g"] == 1000
        # 0.010 kg * 50 + 0.100 kg * 80 = 0.5 + 8 = 8.5
        assert abs(doc["total_cost"] - 8.5) < 0.01, doc["total_cost"]
        # cost_per_kg = total / yield_g * 1000 = 8.5 / 1000 * 1000 = 8.5
        assert abs(doc["cost_per_kg"] - 8.5) < 0.01, doc["cost_per_kg"]
        assert "_id" not in doc
        created_ids.append(doc["id"])

    def test_list_includes_created(self, session, auth, created_ids):
        assert created_ids, "previous test must have created"
        r = session.get(f"{API}/restaurants/{auth['rid']}/local-subproducts")
        assert r.status_code == 200
        ids = [d["id"] for d in r.json()["data"]]
        assert created_ids[0] in ids

    def test_update_recomputes_total(self, session, auth, created_ids):
        sp_id = created_ids[0]
        payload = {
            "name": "TEST_Соус кукуруза v2",
            "yield_g": 500,  # smaller yield → cost_per_kg doubles
            "ingredients": [
                {"name": "Соль", "qty": 10, "unit": "г", "unit_factor": 0.001, "unit_cost": 50.0},
                {"name": "Сахар", "qty": 100, "unit": "г", "unit_factor": 0.001, "unit_cost": 80.0},
            ],
            "notes": "TEST iter21 updated",
        }
        r = session.put(f"{API}/restaurants/{auth['rid']}/local-subproducts/{sp_id}", json=payload)
        assert r.status_code == 200, r.text
        doc = r.json()
        assert doc["name"] == "TEST_Соус кукуруза v2"
        assert doc["yield_g"] == 500
        assert abs(doc["total_cost"] - 8.5) < 0.01
        # cost_per_kg = 8.5 / 500 * 1000 = 17.0
        assert abs(doc["cost_per_kg"] - 17.0) < 0.01, doc["cost_per_kg"]
        assert "_id" not in doc

        # Verify GET reflects update
        r2 = session.get(f"{API}/restaurants/{auth['rid']}/local-subproducts")
        match = next(d for d in r2.json()["data"] if d["id"] == sp_id)
        assert match["name"] == "TEST_Соус кукуруза v2"
        assert abs(match["cost_per_kg"] - 17.0) < 0.01

    def test_cost_catalog_includes_local_subproducts(self, session, auth, created_ids):
        """Even when Caffesta is not configured, cost-catalog should include
        local subproducts marked is_local_subproduct=true."""
        r = session.get(f"{API}/restaurants/{auth['rid']}/cost-catalog")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        local_entries = [d for d in body["data"] if d.get("is_local_subproduct")]
        assert len(local_entries) >= 1, "expected at least 1 local subproduct in catalog"
        sp_id = created_ids[0]
        match = next((d for d in local_entries if d.get("local_subproduct_id") == sp_id), None)
        assert match is not None, f"created subproduct {sp_id} not found in catalog"
        assert match["type"] == "local_subproduct"
        assert match["caffesta_product_id"] is None
        assert match["self_cost"] > 0  # should have cost_per_kg

    def test_delete_returns_in_use_count(self, session, auth, created_ids):
        sp_id = created_ids[0]
        r = session.delete(f"{API}/restaurants/{auth['rid']}/local-subproducts/{sp_id}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body == {"ok": True, "deleted": 1, "in_use_recipes": 0}

        # Verify deletion via list
        r2 = session.get(f"{API}/restaurants/{auth['rid']}/local-subproducts")
        ids = [d["id"] for d in r2.json()["data"]]
        assert sp_id not in ids
        created_ids.clear()

    def test_delete_404_when_missing(self, session, auth):
        r = session.delete(f"{API}/restaurants/{auth['rid']}/local-subproducts/does-not-exist")
        assert r.status_code == 404

    def test_create_validates_empty_name(self, session, auth):
        r = session.post(
            f"{API}/restaurants/{auth['rid']}/local-subproducts",
            json={"name": "  ", "yield_g": 100, "ingredients": []},
        )
        assert r.status_code == 400


# ---------- AI recipe parser ----------

class TestAIParseRecipe:
    SAMPLE = (
        "Соус кукуруза п/ф\n"
        "Соль 10\n"
        "Выход 1000\n"
        "\n"
        "Паста с креветками\n"
        "Соус кукуруза п/ф 150\n"
        "Выход 310\n"
    )

    def test_ai_parse_two_blocks(self, session, auth):
        r = session.post(
            f"{API}/restaurants/{auth['rid']}/recipes/ai-parse",
            json={"text": self.SAMPLE},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "blocks" in body and "stats" in body
        assert body["stats"]["blocks"] == 2
        kinds = [b["kind"] for b in body["blocks"]]
        assert kinds == ["subproduct", "dish"]
        assert body["blocks"][0]["title"].startswith("Соус кукуруза")
        assert body["blocks"][0]["yield_g"] == 1000
        assert body["blocks"][1]["yield_g"] == 310
        # Inline subproduct should be matched in dish block
        dish = body["blocks"][1]
        soup_line = next(i for i in dish["ingredients"] if "Соус кукуруза" in i["name"])
        assert soup_line["matched"] is not None
        assert soup_line["matched"]["type"] == "inline_subproduct"

    def test_ai_parse_empty_text_400(self, session, auth):
        r = session.post(
            f"{API}/restaurants/{auth['rid']}/recipes/ai-parse",
            json={"text": "   "},
        )
        assert r.status_code == 400

    def test_ai_parse_works_with_local_subproducts(self, session, auth):
        """Create a local subproduct, then check ai-parse matches it
        by name even though Caffesta is unavailable in preview."""
        # Create local subproduct
        cr = session.post(
            f"{API}/restaurants/{auth['rid']}/local-subproducts",
            json={
                "name": "TEST_Майонез домашний",
                "yield_g": 500,
                "ingredients": [
                    {"name": "Масло", "qty": 200, "unit": "г",
                     "unit_factor": 0.001, "unit_cost": 100.0},
                ],
            },
        )
        assert cr.status_code == 200
        sp_id = cr.json()["id"]

        try:
            text = "Салат\nМайонез домашний п/ф 50\nВыход 200"
            r = session.post(
                f"{API}/restaurants/{auth['rid']}/recipes/ai-parse",
                json={"text": text},
            )
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["stats"]["blocks"] == 1
            ing = body["blocks"][0]["ingredients"][0]
            assert ing["matched"] is not None, "local subproduct should match"
            assert ing["matched"]["type"] == "local_subproduct"
            assert ing["matched"]["local_subproduct_id"] == sp_id
        finally:
            session.delete(f"{API}/restaurants/{auth['rid']}/local-subproducts/{sp_id}")
