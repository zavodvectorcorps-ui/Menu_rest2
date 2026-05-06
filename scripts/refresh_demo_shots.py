"""Capture screenshots for the marketing /demo page.

Admin pages → desktop (1440 wide) — they are designed for desktop usage.
Client menu → mobile (420 wide retina) — shown in phone-frame mockups.

Run from /app: python3 scripts/refresh_demo_shots.py
"""
import asyncio
import os
import sys
from pathlib import Path

from playwright.async_api import async_playwright

BASE = os.environ.get(
    "DEMO_BASE_URL",
    "https://recipe-calc-preview.preview.emergentagent.com",
)
DEMO_LOGIN = "demo"
DEMO_PASSWORD = "demo2026"

OUT = Path("/app/frontend/public/demo-shots")
OUT.mkdir(parents=True, exist_ok=True)

DESKTOP_VIEW = {"width": 1440, "height": 900}
MENU_VIEW = {"width": 420, "height": 900}    # client menu — phone


async def wait_imgs(page, n=4, timeout=10000):
    try:
        await page.wait_for_function(
            f"""() => {{
                const imgs = Array.from(document.querySelectorAll('img'));
                if (imgs.length === 0) return true;
                const top = imgs.slice(0, {n});
                return top.every(i => i.complete && i.naturalWidth > 0);
            }}""",
            timeout=timeout,
        )
    except Exception:
        pass


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Admin context — desktop
        ctx = await browser.new_context(
            viewport=DESKTOP_VIEW,
            device_scale_factor=1,
        )
        page = await ctx.new_page()

        # ---------- Auth as demo ----------
        resp = await page.request.post(f"{BASE}/api/auth/login",
                                       data={"username": DEMO_LOGIN, "password": DEMO_PASSWORD})
        data = await resp.json()
        token = data["access_token"]
        user = data["user"]
        restaurants = data["restaurants"]
        rid = restaurants[0]["id"]
        import json as _j
        await page.goto(f"{BASE}/login")
        await page.wait_for_timeout(500)
        await page.evaluate(f"""() => {{
            localStorage.setItem('token', {_j.dumps(token)});
            localStorage.setItem('user', {_j.dumps(_j.dumps(user))});
            localStorage.setItem('restaurants', {_j.dumps(_j.dumps(restaurants))});
            localStorage.setItem('currentRestaurantId', {_j.dumps(rid)});
        }}""")

        # ---------- Admin pages (mobile) ----------
        for url, name in [
            ("/admin/orders", "orders"),
            ("/admin/analytics", "analytics"),
            ("/admin/menu", "menu_admin"),
        ]:
            for attempt in range(3):
                try:
                    await page.goto(f"{BASE}{url}", wait_until="domcontentloaded", timeout=25000)
                    break
                except Exception as e:
                    print(f"retry {name} ({attempt+1}/3): {e}")
                    await page.wait_for_timeout(2000)
            await page.wait_for_timeout(5000)
            await wait_imgs(page, n=3, timeout=10000)
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass
            await page.wait_for_timeout(700)
            out = OUT / f"{name}.jpg"
            await page.screenshot(path=str(out), quality=82, type="jpeg", full_page=False)
            print(f"saved {out} ({out.stat().st_size // 1024} KB)")

        # ---------- Client menu (mobile, EN) ----------
        await ctx.close()
        ctx = await browser.new_context(
            viewport=MENU_VIEW,
            device_scale_factor=2,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        )
        page = await ctx.new_page()
        for i, scroll in enumerate([0, 600]):
            for attempt in range(3):
                try:
                    await page.goto(f"{BASE}/myata/1", wait_until="domcontentloaded", timeout=30000)
                    break
                except Exception as e:
                    print(f"retry menu ({attempt+1}/3): {e}")
                    await page.wait_for_timeout(2000)
            # Force EN
            await page.evaluate("() => localStorage.setItem('client_menu_lang','en')")
            await page.reload(wait_until="domcontentloaded")
            await wait_imgs(page, n=6, timeout=15000)
            await page.wait_for_timeout(1500)
            if scroll:
                await page.evaluate(f"window.scrollTo(0, {scroll})")
                await page.wait_for_timeout(1500)
                await wait_imgs(page, n=6, timeout=8000)
            await page.wait_for_timeout(800)
            name = "client_menu_en" if i == 0 else "client_menu_scrolled"
            out = OUT / f"{name}.jpg"
            await page.screenshot(path=str(out), quality=82, type="jpeg", full_page=False)
            print(f"saved {out} ({out.stat().st_size // 1024} KB)")

        await ctx.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
