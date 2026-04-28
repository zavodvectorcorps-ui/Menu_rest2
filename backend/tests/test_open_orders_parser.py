"""Unit test for HTML parser of Caffesta admin orders_history page.
The actual fetch is mocked. We feed a synthetic HTML close to the real layout
and verify rows are extracted with correct time/total/table fields.
"""
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from services.caffesta import caffesta_fetch_open_orders


SAMPLE_HTML = """
<!DOCTYPE html>
<html><body>
<h1>История счетов</h1>
<table class="orders">
  <thead><tr><th>#</th><th>Стол</th><th>Открыт</th><th>Последнее действие</th><th>Сумма</th></tr></thead>
  <tbody>
    <tr><td>1234</td><td>Стол 5</td><td>2026-02-12 19:30</td><td>2026-02-12 22:45</td><td>87.50 BYN</td></tr>
    <tr><td>1235</td><td>Стол 12</td><td>2026-02-12 20:10</td><td>2026-02-12 23:15</td><td>156.20 BYN</td></tr>
    <tr><td>1236</td><td>Стол 3</td><td>2026-02-12 21:00</td><td>2026-02-12 23:55</td><td>42.00 BYN</td></tr>
  </tbody>
</table>
</body></html>
"""

LOGIN_HTML = """
<html><body>
<form><input type="password" name="pw"/><input type="submit"/></form>
</body></html>
"""


@pytest.mark.asyncio
async def test_parser_extracts_rows():
    fake_resp = MagicMock(status_code=200, text=SAMPLE_HTML)
    fake_cfg = {"account_name": "demo", "admin_session_cookie": "PHPSESSID_VALUE"}

    with patch("services.caffesta.get_caffesta_config", new=AsyncMock(return_value=fake_cfg)), \
         patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=fake_resp)
        res = await caffesta_fetch_open_orders("rid")
    assert res["ok"] is True
    assert len(res["data"]) == 3
    first = res["data"][0]
    assert first["last_action_at"] is not None
    assert first["total"] is not None
    assert first["total"] > 0
    # Table number must be detected
    assert any(r.get("table") == "5" for r in res["data"])


@pytest.mark.asyncio
async def test_parser_session_expired():
    fake_resp = MagicMock(status_code=200, text=LOGIN_HTML)
    fake_cfg = {"account_name": "demo", "admin_session_cookie": "STALE"}

    with patch("services.caffesta.get_caffesta_config", new=AsyncMock(return_value=fake_cfg)), \
         patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=fake_resp)
        res = await caffesta_fetch_open_orders("rid")
    assert res["ok"] is False
    assert res["reason"] == "session_expired"


@pytest.mark.asyncio
async def test_no_cookie():
    fake_cfg = {"account_name": "demo"}
    with patch("services.caffesta.get_caffesta_config", new=AsyncMock(return_value=fake_cfg)):
        res = await caffesta_fetch_open_orders("rid")
    assert res["ok"] is False
    assert res["reason"] == "no_cookie"


@pytest.mark.asyncio
async def test_redirect_to_login():
    fake_resp = MagicMock(status_code=302, text="")
    fake_cfg = {"account_name": "demo", "admin_session_cookie": "STALE"}
    with patch("services.caffesta.get_caffesta_config", new=AsyncMock(return_value=fake_cfg)), \
         patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=fake_resp)
        res = await caffesta_fetch_open_orders("rid")
    assert res["ok"] is False
    assert res["reason"] == "session_expired"


@pytest.mark.asyncio
async def test_parser_does_not_confuse_id_with_amount():
    """Regression: order id '#116497' must NOT be parsed as 116497 BYN amount.
    The real amount has decimal part."""
    html = """
    <html><body><table>
    <tr><td>#116497</td><td>21:35</td><td>21:35</td><td>87.50 BYN</td></tr>
    <tr><td>#116499</td><td>21:33</td><td>21:33</td><td>156,20 BYN</td></tr>
    </table></body></html>
    """
    fake_resp = MagicMock(status_code=200, text=html)
    fake_cfg = {"account_name": "demo", "admin_session_cookie": "X"}
    with patch("services.caffesta.get_caffesta_config", new=AsyncMock(return_value=fake_cfg)), \
         patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=fake_resp)
        res = await caffesta_fetch_open_orders("rid")
    assert res["ok"] is True
    totals = [r["total"] for r in res["data"]]
    # Must be the real money values, not the order id 116497
    assert 87.5 in totals
    assert 156.2 in totals
    assert 116497 not in totals
    assert 116499 not in totals


if __name__ == "__main__":
    asyncio.run(test_parser_extracts_rows())
    asyncio.run(test_parser_session_expired())
    asyncio.run(test_no_cookie())
    asyncio.run(test_redirect_to_login())
    print("OK")
