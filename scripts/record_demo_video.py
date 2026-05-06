"""Records a 30-sec demo screencast of the REST-MENU app for marketing.
Run from /app: python3 scripts/record_demo_video.py

Output: /app/frontend/public/demo.webm (then optionally convert to mp4)
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

# Demo creds — must match those seeded by /api/seed
DEMO_LOGIN = "demo"
DEMO_PASSWORD = "demo2026"

# Output
OUT_DIR = Path("/app/frontend/public")
TMP_VIDEO_DIR = Path("/tmp/demo_videos")
TMP_VIDEO_DIR.mkdir(parents=True, exist_ok=True)


async def slow_scroll(page, target_y, steps=20, delay=30):
    cur_y = await page.evaluate("window.scrollY")
    diff = target_y - cur_y
    for i in range(steps):
        y = cur_y + diff * (i + 1) / steps
        await page.evaluate(f"window.scrollTo(0, {y})")
        await page.wait_for_timeout(delay)


async def main():
    async with async_playwright() as p:
        # Use a phone-ish viewport for the client menu portion
        # Recording is captured for the entire context, so use a clean 1280x720 size
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        ctx = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(TMP_VIDEO_DIR),
            record_video_size={"width": 1280, "height": 720},
        )
        page = await ctx.new_page()

        # ---------- Scene 1: Client menu (gosti) ----------
        await page.goto(f"{BASE}/myata/1", wait_until="networkidle", timeout=30000)
        # Wait for menu images to actually load (otherwise dish photos appear black)
        try:
            await page.wait_for_function(
                """() => {
                    const imgs = Array.from(document.querySelectorAll('img'));
                    if (imgs.length < 3) return false;
                    const top = imgs.slice(0, 6);
                    return top.every(i => i.complete && i.naturalWidth > 0);
                }""",
                timeout=15000,
            )
        except Exception:
            pass
        await page.wait_for_timeout(1500)
        # Slow scroll through menu
        await slow_scroll(page, 800, steps=40, delay=40)
        await page.wait_for_timeout(800)
        # Try toggling language to EN
        try:
            await page.click('[data-testid="lang-btn-en"]', timeout=3000)
            await page.wait_for_timeout(1200)
            await slow_scroll(page, 1400, steps=30, delay=40)
        except Exception:
            pass
        await page.wait_for_timeout(800)

        # ---------- Scene 2: Admin login -> orders ----------
        # API login then inject token
        try:
            resp = await page.request.post(f"{BASE}/api/auth/login", data={"username": DEMO_LOGIN, "password": DEMO_PASSWORD})
            data = await resp.json()
            token = data.get("access_token")
            user = data.get("user")
            restaurants = data.get("restaurants") or []
            rid = restaurants[0]["id"] if restaurants else ""
            import json as _json
            await page.goto(f"{BASE}/login", wait_until="domcontentloaded")
            await page.evaluate(f"""() => {{
                localStorage.setItem('token', {_json.dumps(token)});
                localStorage.setItem('user', {_json.dumps(_json.dumps(user))});
                localStorage.setItem('restaurants', {_json.dumps(_json.dumps(restaurants))});
                localStorage.setItem('currentRestaurantId', {_json.dumps(rid)});
            }}""")
            # Orders
            await page.goto(f"{BASE}/admin/orders", wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(2000)
            await slow_scroll(page, 600, steps=25, delay=40)
            # Analytics
            await page.goto(f"{BASE}/admin/analytics", wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(2200)
            await slow_scroll(page, 800, steps=30, delay=40)
        except Exception as e:
            print("Admin scene error:", e)

        # Close to flush video
        await ctx.close()
        await browser.close()

    # Find the latest .webm in tmp dir
    webms = sorted(TMP_VIDEO_DIR.glob("*.webm"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not webms:
        print("ERROR: no video produced")
        sys.exit(1)
    src = webms[0]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dest_webm = OUT_DIR / "demo.webm"
    dest_webm.write_bytes(src.read_bytes())
    size_kb = dest_webm.stat().st_size // 1024
    print(f"Saved {dest_webm} — {size_kb} KB")

    # Try converting to mp4 with ffmpeg if available
    mp4 = OUT_DIR / "demo.mp4"
    rc = os.system(
        f'ffmpeg -y -i "{dest_webm}" -c:v libx264 -preset fast -crf 28 '
        f'-pix_fmt yuv420p -movflags +faststart "{mp4}" 2>/dev/null'
    )
    if rc == 0 and mp4.exists():
        print(f"Saved {mp4} — {mp4.stat().st_size // 1024} KB")
    else:
        print("ffmpeg conversion skipped (mp4 not produced)")


if __name__ == "__main__":
    asyncio.run(main())
