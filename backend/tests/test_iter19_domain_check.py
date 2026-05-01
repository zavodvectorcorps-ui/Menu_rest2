"""Iteration 19 — custom domain diagnostic endpoint.

GET /api/restaurants/{rid}/domains/check?domain=X
Covers: DNS check, HTTPS reachability, DB binding, auth gates, normalization.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback to frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

MYATA_ID = "aa25189d-d668-4838-915a-c5d936547f3f"

SUPER = {"username": "admin", "password": "220066"}
ADMIN = {"username": "admin_test", "password": "test123456"}


@pytest.fixture(scope="module")
def super_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=SUPER, timeout=10)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN, timeout=10)
    if r.status_code != 200:
        pytest.skip("admin_test login unavailable")
    return r.json()["access_token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


# ---------- Auth gates ----------
def test_check_requires_auth():
    r = requests.get(
        f"{BASE_URL}/api/restaurants/{MYATA_ID}/domains/check",
        params={"domain": "example.com"}, timeout=10,
    )
    assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"


def test_check_requires_superadmin(admin_token):
    r = requests.get(
        f"{BASE_URL}/api/restaurants/{MYATA_ID}/domains/check",
        headers=_h(admin_token), params={"domain": "example.com"}, timeout=10,
    )
    assert r.status_code in (401, 403), f"non-super should be forbidden, got {r.status_code}"


# ---------- Happy paths ----------
def test_check_nonexistent_domain_dns_error(super_token):
    r = requests.get(
        f"{BASE_URL}/api/restaurants/{MYATA_ID}/domains/check",
        headers=_h(super_token),
        params={"domain": "nonexistent-zzz12345.example.invalid"},
        timeout=20,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["overall"] == "error"
    assert data["dns"]["ok"] is False
    assert "DNS" in data["summary"] or "A-запись" in data["summary"]


def test_check_real_domain_returns_structured(super_token):
    r = requests.get(
        f"{BASE_URL}/api/restaurants/{MYATA_ID}/domains/check",
        headers=_h(super_token), params={"domain": "rest-menu.by"}, timeout=20,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["domain"] == "rest-menu.by"
    assert data["dns"]["ok"] is True
    assert data["dns"]["ips"], "expected IPs for rest-menu.by"
    # overall should be ok or warning (depends on binding & https)
    assert data["overall"] in ("ok", "warning"), data
    assert "https" in data and "binding" in data


def test_check_empty_domain_returns_400(super_token):
    r = requests.get(
        f"{BASE_URL}/api/restaurants/{MYATA_ID}/domains/check",
        headers=_h(super_token), params={"domain": ""}, timeout=10,
    )
    assert r.status_code == 400, r.text


def test_check_normalizes_scheme_port_path(super_token):
    r = requests.get(
        f"{BASE_URL}/api/restaurants/{MYATA_ID}/domains/check",
        headers=_h(super_token),
        params={"domain": "HTTPS://Rest-Menu.by:443/foo"},
        timeout=20,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["domain"] == "rest-menu.by"


def test_check_unknown_restaurant_404(super_token):
    r = requests.get(
        f"{BASE_URL}/api/restaurants/00000000-0000-0000-0000-000000000000/domains/check",
        headers=_h(super_token), params={"domain": "example.com"}, timeout=10,
    )
    assert r.status_code == 404


# ---------- Regression ----------
def test_regression_put_custom_domains_and_menu_by_domain(super_token):
    """Make sure earlier endpoints (iter18) still work."""
    # Attach a test domain
    test_dom = "rest-menu.by"
    r = requests.put(
        f"{BASE_URL}/api/restaurants/{MYATA_ID}",
        headers=_h(super_token),
        json={"custom_domains": [test_dom]}, timeout=10,
    )
    assert r.status_code == 200, r.text
    try:
        # Verify check endpoint says binding.ok=True now
        r2 = requests.get(
            f"{BASE_URL}/api/restaurants/{MYATA_ID}/domains/check",
            headers=_h(super_token), params={"domain": test_dom}, timeout=20,
        )
        assert r2.status_code == 200
        d = r2.json()
        assert d["binding"]["ok"] is True
        assert d["binding"]["bound_to"]["id"] == MYATA_ID

        # menu-by-domain still works
        r3 = requests.get(
            f"{BASE_URL}/api/public/menu-by-domain/1",
            params={"host": test_dom}, timeout=10,
        )
        # Should be 200 (table 1 exists for Мята) or 404 (no table)
        assert r3.status_code in (200, 404), r3.text
    finally:
        # restore
        requests.put(
            f"{BASE_URL}/api/restaurants/{MYATA_ID}",
            headers=_h(super_token), json={"custom_domains": []}, timeout=10,
        )


def test_regression_qr_pdf_still_works(super_token):
    # Find a table id
    r = requests.get(
        f"{BASE_URL}/api/restaurants/{MYATA_ID}/tables",
        headers=_h(super_token), timeout=10,
    )
    assert r.status_code == 200
    tables = r.json()
    if not tables:
        pytest.skip("no tables to test qr-pdf")
    tid = tables[0]["id"]
    r2 = requests.get(
        f"{BASE_URL}/api/restaurants/{MYATA_ID}/tables/{tid}/qr-pdf",
        headers=_h(super_token), params={"size": "a5"}, timeout=15,
    )
    assert r2.status_code == 200
    assert r2.headers.get("content-type", "").startswith("application/pdf")
    assert r2.content[:4] == b"%PDF"
