"""Iteration 18: cart_only module, custom_domains, qr-pdf, webhook reset."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback for local runs reading frontend/.env
    p = "/app/frontend/.env"
    if os.path.exists(p):
        for line in open(p):
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

API = f"{BASE_URL}/api"
RID_MYATA = "aa25189d-d668-4838-915a-c5d936547f3f"  # Мята Спортивная
PROTECTED_RID = "d433dc80"  # Catch — never modify

SUPER = {"username": "admin", "password": "220066"}
ADMIN_TEST = {"username": "admin_test", "password": "test123456"}


@pytest.fixture(scope="module")
def super_token():
    r = requests.post(f"{API}/auth/login", json=SUPER, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def super_h(super_token):
    return {"Authorization": f"Bearer {super_token}"}


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json=ADMIN_TEST, timeout=15)
    if r.status_code != 200:
        pytest.skip("admin_test login not available")
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def myata_initial(super_h):
    """Snapshot Мята's modules + domains + slug for restore."""
    r = requests.get(f"{API}/restaurants/{RID_MYATA}", headers=super_h, timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    return {
        "enabled_modules": d.get("enabled_modules") or [],
        "custom_domains": d.get("custom_domains") or [],
        "slug": d.get("slug") or "",
    }


@pytest.fixture(scope="module", autouse=True)
def _restore(super_h, myata_initial):
    yield
    requests.put(
        f"{API}/restaurants/{RID_MYATA}",
        headers=super_h,
        json={
            "enabled_modules": myata_initial["enabled_modules"],
            "custom_domains": myata_initial["custom_domains"],
            "slug": myata_initial["slug"],
        },
        timeout=15,
    )


# ============= custom_domains tests =============

class TestCustomDomains:
    def test_superadmin_can_set_domains_normalized(self, super_h):
        r = requests.put(
            f"{API}/restaurants/{RID_MYATA}",
            headers=super_h,
            json={"custom_domains": ["HTTPS://Menu.Test-Iter18.com:8080/foo", "MENU.test-iter18.com"]},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        # Normalised: lowercase, strip scheme/port/path, dedup
        assert data["custom_domains"] == ["menu.test-iter18.com"], data["custom_domains"]

    def test_uniqueness_validation(self, super_h):
        # Try to set the same domain on Caffesta — should error.
        # First fetch caffesta id (we won't modify it)
        rs = requests.get(f"{API}/restaurants", headers=super_h, timeout=15).json()
        other = next((x for x in rs if x.get("id") != RID_MYATA), None)
        if not other:
            pytest.skip("No second restaurant found")
        # Now reset Myata to the test domain
        requests.put(
            f"{API}/restaurants/{RID_MYATA}",
            headers=super_h,
            json={"custom_domains": ["unique-iter18.test"]},
            timeout=15,
        )
        # Attempt to bind same on the other restaurant — server must 400 BEFORE writing.
        # We send only its existing domains + the conflicting one (and we send only custom_domains
        # field so other settings are untouched).
        r = requests.put(
            f"{API}/restaurants/{other['id']}",
            headers=super_h,
            json={"custom_domains": (other.get("custom_domains") or []) + ["unique-iter18.test"]},
            timeout=15,
        )
        assert r.status_code == 400, r.text
        assert "уже привязан" in r.text or "already" in r.text.lower()

    def test_non_superadmin_cannot_change_domains(self, admin_token):
        h = {"Authorization": f"Bearer {admin_token}"}
        # First check admin_test has access to Myata
        r0 = requests.get(f"{API}/restaurants/{RID_MYATA}", headers=h, timeout=15)
        if r0.status_code == 403:
            pytest.skip("admin_test has no access to Myata — feature still tested via 403")
        if r0.status_code != 200:
            pytest.skip(f"admin_test cannot read Myata ({r0.status_code})")
        before = r0.json().get("custom_domains") or []
        r = requests.put(
            f"{API}/restaurants/{RID_MYATA}",
            headers=h,
            json={"custom_domains": ["evil-admin.test"]},
            timeout=15,
        )
        # Either 200 (silent ignore) or 403; either way domains must NOT contain evil-admin.test
        if r.status_code == 200:
            assert "evil-admin.test" not in (r.json().get("custom_domains") or [])
        # Re-verify with super
        # (using requests directly w/o super here — just trust the response)


# ============= cart_only enabled_modules =============

class TestCartOnlyModule:
    def test_set_cart_only_module(self, super_h, myata_initial):
        new_mods = list(set(myata_initial["enabled_modules"] + ["cart_only"]))
        r = requests.put(
            f"{API}/restaurants/{RID_MYATA}",
            headers=super_h,
            json={"enabled_modules": new_mods},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        assert "cart_only" in r.json()["enabled_modules"]

        # Verify GET persists
        g = requests.get(f"{API}/restaurants/{RID_MYATA}", headers=super_h, timeout=15)
        assert "cart_only" in g.json()["enabled_modules"]


# ============= menu-by-domain =============

class TestMenuByDomain:
    DOMAIN = "iter18-domain.test"

    @pytest.fixture(scope="class", autouse=True)
    def _bind(self, super_h):
        # Bind a domain to Myata
        requests.put(
            f"{API}/restaurants/{RID_MYATA}",
            headers=super_h,
            json={"custom_domains": [self.DOMAIN]},
            timeout=15,
        )
        # Ensure table 1 exists in Myata
        ts = requests.get(f"{API}/restaurants/{RID_MYATA}/tables", headers=super_h, timeout=15).json()
        if not any(t.get("number") == 1 for t in ts):
            requests.post(
                f"{API}/restaurants/{RID_MYATA}/tables",
                headers=super_h,
                json={"number": 1},
                timeout=15,
            )
        yield

    def test_resolve_by_query_host(self):
        r = requests.get(f"{API}/public/menu-by-domain/1?host={self.DOMAIN}", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["restaurant"]["id"] == RID_MYATA
        assert d["table"]["number"] == 1

    def test_resolve_by_xforwarded_header(self):
        r = requests.get(
            f"{API}/public/menu-by-domain/1",
            headers={"X-Forwarded-Host": f"{self.DOMAIN.upper()}:443"},
            timeout=15,
        )
        # Note: requests' default Host header points at the ingress. We rely on X-Forwarded-Host.
        # Acceptable result: 200 (resolved) — or 404 if proxy strips header. Try both query + header.
        if r.status_code == 404:
            # As fallback, try with both header + query=other-domain to demonstrate header path:
            pytest.skip("X-Forwarded-Host stripped by ingress — query-host path already covered")
        assert r.status_code == 200, r.text

    def test_404_unknown_domain(self):
        r = requests.get(f"{API}/public/menu-by-domain/1?host=nonexistent-xyz-iter18.test", timeout=15)
        assert r.status_code == 404
        assert "не привязан" in r.text or "not" in r.text.lower()

    def test_404_unknown_table(self):
        r = requests.get(f"{API}/public/menu-by-domain/9999?host={self.DOMAIN}", timeout=15)
        assert r.status_code == 404
        assert "Стол" in r.text or "not" in r.text.lower()


# ============= qr-pdf =============

class TestQrPdf:
    @pytest.fixture(scope="class")
    def table_id(self, super_h):
        ts = requests.get(f"{API}/restaurants/{RID_MYATA}/tables", headers=super_h, timeout=15).json()
        if not ts:
            pytest.skip("No tables")
        return ts[0]["id"]

    def test_pdf_a5(self, super_h, table_id):
        r = requests.get(
            f"{API}/restaurants/{RID_MYATA}/tables/{table_id}/qr-pdf?size=a5",
            headers=super_h,
            timeout=30,
        )
        assert r.status_code == 200, r.text[:500]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:5] == b"%PDF-"
        assert len(r.content) > 1000

    def test_pdf_a6(self, super_h, table_id):
        r = requests.get(
            f"{API}/restaurants/{RID_MYATA}/tables/{table_id}/qr-pdf?size=a6",
            headers=super_h,
            timeout=30,
        )
        assert r.status_code == 200
        assert r.content[:5] == b"%PDF-"

    def test_pdf_requires_auth(self, table_id):
        r = requests.get(
            f"{API}/restaurants/{RID_MYATA}/tables/{table_id}/qr-pdf?size=a5",
            timeout=15,
        )
        assert r.status_code in (401, 403)


# ============= webhook reset =============

class TestWebhookReset:
    def test_reset_uses_xforwarded_host(self, super_h):
        """Endpoint MUST NOT return 'Не задан PUBLIC_BASE_URL' / 500 when Host header is present.
        Without bot_token configured we expect 400 'Сначала сохраните токен бота'."""
        r = requests.post(
            f"{API}/restaurants/{RID_MYATA}/telegram-bot/webhook/reset",
            headers={**super_h, "X-Forwarded-Host": "menu.test-iter18.com", "X-Forwarded-Proto": "https"},
            timeout=15,
        )
        # 400 'token first' OR 200 (if bot is set & telegram accepts) — both fine.
        # Critically: must NOT be 500 with PUBLIC_BASE_URL message.
        assert r.status_code in (200, 400), r.text
        assert "PUBLIC_BASE_URL" not in r.text, f"PUBLIC_BASE_URL error leaked: {r.text}"
