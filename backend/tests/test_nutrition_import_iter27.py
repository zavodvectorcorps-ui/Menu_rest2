"""Iteration 27 additional regression tests: new scoring formula (0.6*token_sort + 0.4*token_set) without partial_ratio."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"
SAMPLE = "/tmp/bzu.docx"


def test_short_query_vs_long_choice_matches():
    """query='Сырники', choice='Сырники ванильным кремом' → score ≈ 0.6*45+0.4*100 = 67 ≥ 65 → matched."""
    from services.nutrition_import import match_records_to_items
    items = [
        {"id": "s", "name": "Сырники ванильным кремом"},
        {"id": "o", "name": "Совершенно другое блюдо"},
    ]
    records = [{"name": "Сырники", "protein": 10, "fat": 15, "carbs": 20, "kcal": 300, "kj": 1256}]
    res = match_records_to_items(records, items)
    matched_sources = [m["source"] for m in res["matched"]]
    assert "Сырники" in matched_sources, f"expected matched, got {res}"


def test_word_permutation_matches():
    """query='ролл калифорния' vs choice='калифорния ролл' → both ratios = 100 → matched."""
    from services.nutrition_import import match_records_to_items
    items = [
        {"id": "r", "name": "калифорния ролл"},
        {"id": "o", "name": "Абсолютно другое блюдо xyz"},
    ]
    records = [{"name": "ролл калифорния", "protein": 5, "fat": 5, "carbs": 20, "kcal": 150, "kj": 628}]
    res = match_records_to_items(records, items)
    matched = [m for m in res["matched"] if m["source"] == "ролл калифорния"]
    assert matched, f"expected matched, got {res}"
    assert matched[0]["score"] >= 95


def test_isolated_syrniki_vs_cheeseburger_no_false_match():
    """Isolated 2-item test: Сырники должны быть в unmatched (best_score<65) или ambiguous, но НЕ в matched."""
    from services.nutrition_import import match_records_to_items
    items = [
        {"id": "cb", "name": "Чизбургер с вишневым соусом"},
        {"id": "p", "name": "Паста Карбонара"},
    ]
    records = [{
        "name": "Сырники с ванильным кремом и вишневым соусом",
        "protein": 11.15, "fat": 16.37, "carbs": 28.74, "kcal": 306, "kj": 1285,
    }]
    res = match_records_to_items(records, items)
    matched_sources = [m["source"] for m in res["matched"]]
    assert "Сырники с ванильным кремом и вишневым соусом" not in matched_sources, (
        f"REGRESSION: Сырники auto-matched to Чизбургер. res={res}"
    )


# ---------- real file distribution ----------
@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"username": "admin", "password": "220066"}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def restaurant_id(auth_headers):
    r = requests.get(f"{API}/restaurants", headers=auth_headers, timeout=15)
    rests = r.json()
    for x in rests:
        if x.get("slug") != "demo":
            return x["id"]
    return rests[0]["id"]


def test_real_file_distribution(auth_headers, restaurant_id):
    """Real /tmp/bzu.docx → matched≈46, unmatched≈17, ambiguous≈4, ≥30 with score>=95, Сырники in unmatched."""
    if not os.path.exists(SAMPLE):
        pytest.skip("no sample file")
    with open(SAMPLE, "rb") as f:
        blob = f.read()
    files = {"file": ("bzu.docx", blob,
                      "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    r = requests.post(
        f"{API}/restaurants/{restaurant_id}/menu-items/nutrition-import",
        headers=auth_headers, files=files, params={"dry_run": "true"}, timeout=60,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    m, a, u = len(data["matched"]), len(data["ambiguous"]), len(data["unmatched"])
    print(f"\n>>> distribution: matched={m}, ambiguous={a}, unmatched={u}, total={data['records_total']}")

    assert data["records_total"] == 67
    assert m + a + u == 67

    # Loose bounds around expected values
    assert 40 <= m <= 55, f"matched out of expected range: {m}"
    assert 10 <= u <= 25, f"unmatched out of expected range: {u}"
    assert 0 <= a <= 10, f"ambiguous out of expected range: {a}"

    # score distribution: ≥30 records с score >=95
    high_score = sum(1 for x in data["matched"] if x["score"] >= 95)
    print(f">>> high_score(>=95)={high_score}")
    assert high_score >= 30, f"expected >=30 matched with score>=95, got {high_score}"

    # Сырники должен быть в unmatched
    unmatched_srcs = [u["source"].lower() for u in data["unmatched"]]
    ambiguous_srcs = [a["source"].lower() for a in data["ambiguous"]]
    matched_srcs = [m["source"].lower() for m in data["matched"]]
    syrniki_locations = []
    for src in matched_srcs:
        if "сырники" in src and "ванильн" in src:
            syrniki_locations.append(("matched", src))
    for src in unmatched_srcs:
        if "сырники" in src and "ванильн" in src:
            syrniki_locations.append(("unmatched", src))
    for src in ambiguous_srcs:
        if "сырники" in src and "ванильн" in src:
            syrniki_locations.append(("ambiguous", src))
    print(f">>> Сырники locations: {syrniki_locations}")
    assert not any(loc == "matched" for loc, _ in syrniki_locations), \
        f"Сырники auto-matched: {syrniki_locations}"
