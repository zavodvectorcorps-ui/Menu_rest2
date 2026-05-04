"""Generate a branded share-card PNG for the public demo restaurant.

Returns a 1080x1080 image (square — best for WhatsApp/Telegram previews) with:
- Dark brand background (#0a0e1a) + a soft mint glow
- "REST-MENU" wordmark in mint
- Demo restaurant name + slogan
- Centered QR code that links to the live demo menu
- Footer CTA "Сканируйте → попробуйте меню"

The image is computed on demand and not cached on disk; it's small enough
(~120 KB PNG) that bandwidth is negligible.
"""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
import qrcode
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

BG = (10, 14, 26)           # #0a0e1a
MINT = (93, 169, 164)       # brand mint
MINT_SOFT = (93, 169, 164, 50)
WHITE = (255, 255, 255)
SUBTLE = (180, 195, 210)
DIVIDER = (255, 255, 255, 18)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_REG
    if not Path(path).exists():
        return ImageFont.load_default()
    return ImageFont.truetype(path, size)


def _wrap(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Greedy word-wrap based on font metrics."""
    if not text:
        return []
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        bbox = font.getbbox(test)
        if bbox[2] - bbox[0] <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _draw_glow(img: Image.Image) -> None:
    """Soft radial mint glow in the top-left corner."""
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((-300, -300, 700, 700), fill=(93, 169, 164, 70))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=120))
    img.alpha_composite(glow)

    # purple glow bottom-right
    glow2 = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd2 = ImageDraw.Draw(glow2)
    gd2.ellipse((img.width - 600, img.height - 600, img.width + 300, img.height + 300),
                fill=(140, 90, 200, 60))
    glow2 = glow2.filter(ImageFilter.GaussianBlur(radius=120))
    img.alpha_composite(glow2)


def render_demo_share_card(
    *,
    url: str,
    restaurant_name: str,
    slogan: str = "",
    table_number: int | None = None,
) -> bytes:
    """Compose the PNG and return raw bytes."""
    SIZE = 1080
    img = Image.new("RGBA", (SIZE, SIZE), BG + (255,))
    _draw_glow(img)
    draw = ImageDraw.Draw(img)

    # Header — wordmark
    pad = 80
    f_brand = _font(36, bold=True)
    draw.text((pad, pad), "REST-MENU", font=f_brand, fill=MINT)

    # Subtle eyebrow
    f_eyebrow = _font(22)
    draw.text((pad, pad + 50), "Демо-ресторан · попробуйте платформу", font=f_eyebrow, fill=SUBTLE)

    # Headline (restaurant name)
    f_title = _font(72, bold=True)
    title_lines = _wrap(restaurant_name or "Demo Restaurant", f_title, SIZE - 2 * pad)
    y = pad + 130
    for line in title_lines[:2]:
        draw.text((pad, y), line, font=f_title, fill=WHITE)
        y += 84

    # Slogan
    if slogan:
        f_slogan = _font(32)
        slogan_lines = _wrap(slogan, f_slogan, SIZE - 2 * pad)
        y += 8
        for line in slogan_lines[:2]:
            draw.text((pad, y), line, font=f_slogan, fill=SUBTLE)
            y += 42

    # QR — centered, large, with white frame
    qr = qrcode.QRCode(box_size=10, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
    qr_size = 480
    qr_img = qr_img.resize((qr_size, qr_size), Image.NEAREST)
    qr_x = (SIZE - qr_size) // 2
    qr_y = SIZE - qr_size - 220
    # White rounded panel behind QR
    panel_pad = 28
    panel = (qr_x - panel_pad, qr_y - panel_pad, qr_x + qr_size + panel_pad, qr_y + qr_size + panel_pad)
    panel_img = Image.new("RGBA", img.size, (0, 0, 0, 0))
    pd = ImageDraw.Draw(panel_img)
    pd.rounded_rectangle(panel, radius=32, fill=WHITE)
    img.alpha_composite(panel_img)
    img.alpha_composite(qr_img, dest=(qr_x, qr_y))

    # Footer — CTA + URL
    f_cta = _font(32, bold=True)
    cta_text = "Наведите камеру → попробуйте меню"
    bbox = f_cta.getbbox(cta_text)
    cta_w = bbox[2] - bbox[0]
    draw.text(((SIZE - cta_w) // 2, SIZE - 130), cta_text, font=f_cta, fill=WHITE)

    # URL line
    f_url = _font(20)
    short = url
    if short.startswith("https://"):
        short = short[len("https://"):]
    if short.startswith("http://"):
        short = short[len("http://"):]
    bbox = f_url.getbbox(short)
    url_w = bbox[2] - bbox[0]
    draw.text(((SIZE - url_w) // 2, SIZE - 80), short, font=f_url, fill=MINT)

    # Optional table number badge in top-right
    if table_number is not None:
        f_badge = _font(20, bold=True)
        badge_text = f"СТОЛ №{table_number}"
        bbox = f_badge.getbbox(badge_text)
        bw = bbox[2] - bbox[0] + 36
        bh = 44
        bx = SIZE - pad - bw
        by = pad + 8
        badge = Image.new("RGBA", img.size, (0, 0, 0, 0))
        bd = ImageDraw.Draw(badge)
        bd.rounded_rectangle((bx, by, bx + bw, by + bh), radius=22,
                             fill=(93, 169, 164, 40), outline=MINT, width=2)
        img.alpha_composite(badge)
        draw.text((bx + 18, by + 11), badge_text, font=f_badge, fill=MINT)

    out = BytesIO()
    img.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()


def _fetch_logo(logo_url: str | None) -> Image.Image | None:
    """Best-effort logo fetch. Returns None on any failure (silently)."""
    if not logo_url:
        return None
    try:
        import urllib.request
        if logo_url.startswith(("http://", "https://")):
            req = urllib.request.Request(logo_url, headers={"User-Agent": "rest-menu-share-card/1.0"})
            with urllib.request.urlopen(req, timeout=4) as r:
                data = r.read()
        else:
            # Local path / static
            p = Path(logo_url)
            if not p.is_absolute():
                p = Path("/app/frontend/public") / logo_url.lstrip("/")
            if not p.exists():
                return None
            data = p.read_bytes()
        return Image.open(BytesIO(data)).convert("RGBA")
    except Exception:
        return None


def render_share_card(
    *,
    url: str,
    restaurant_name: str,
    slogan: str = "",
    eyebrow: str = "Цифровое меню по QR",
    cta: str = "Наведите камеру → откройте меню",
    table_number: int | None = None,
    logo_url: str | None = None,
    fmt: str = "square",
) -> bytes:
    """Generalized share-card renderer.

    fmt: "square" (1080x1080, IG/Telegram/WhatsApp) or "story" (1080x1920, IG Stories/Reels).
    """
    is_story = fmt == "story"
    W, H = (1080, 1920) if is_story else (1080, 1080)
    img = Image.new("RGBA", (W, H), BG + (255,))
    _draw_glow(img)
    draw = ImageDraw.Draw(img)

    pad = 80

    # ---- Header: optional logo + brand wordmark ----
    logo = _fetch_logo(logo_url)
    header_y = pad
    if logo:
        # Round-square thumbnail, 96px
        sz = 96
        logo_sq = ImageOps.fit(logo, (sz, sz), method=Image.LANCZOS)
        mask = Image.new("L", (sz, sz), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, sz, sz), radius=24, fill=255)
        img.paste(logo_sq, (pad, header_y), mask)
        text_x = pad + sz + 24
    else:
        text_x = pad

    f_brand = _font(34, bold=True)
    draw.text((text_x, header_y + (8 if logo else 0)), restaurant_name or "REST-MENU", font=f_brand, fill=WHITE)

    f_eyebrow = _font(22)
    draw.text((text_x, header_y + (50 if logo else 50)), eyebrow, font=f_eyebrow, fill=MINT)

    # ---- Slogan / supporting copy block (mid) ----
    f_title = _font(56 if is_story else 60, bold=True)
    headline = slogan or "Отсканируйте QR — попробуйте меню прямо сейчас"
    title_lines = _wrap(headline, f_title, W - 2 * pad)
    y = header_y + 180 + (40 if is_story else 0)
    for line in title_lines[:3]:
        draw.text((pad, y), line, font=f_title, fill=WHITE)
        y += 70

    # ---- QR — large, centered ----
    qr = qrcode.QRCode(box_size=10, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
    qr_size = 560 if is_story else 500
    qr_img = qr_img.resize((qr_size, qr_size), Image.NEAREST)
    qr_x = (W - qr_size) // 2
    # Position: centered vertically in lower half
    qr_y = (H - qr_size) // 2 + (60 if is_story else 60)
    panel_pad = 30
    panel = (qr_x - panel_pad, qr_y - panel_pad, qr_x + qr_size + panel_pad, qr_y + qr_size + panel_pad)
    panel_img = Image.new("RGBA", img.size, (0, 0, 0, 0))
    pd = ImageDraw.Draw(panel_img)
    pd.rounded_rectangle(panel, radius=36, fill=WHITE)
    img.alpha_composite(panel_img)
    img.alpha_composite(qr_img, dest=(qr_x, qr_y))

    # ---- Footer: CTA + URL ----
    f_cta = _font(34, bold=True)
    bbox = f_cta.getbbox(cta)
    cta_w = bbox[2] - bbox[0]
    draw.text(((W - cta_w) // 2, H - 160), cta, font=f_cta, fill=WHITE)

    f_url = _font(22)
    short = url
    for prefix in ("https://", "http://"):
        if short.startswith(prefix):
            short = short[len(prefix):]
            break
    bbox = f_url.getbbox(short)
    url_w = bbox[2] - bbox[0]
    draw.text(((W - url_w) // 2, H - 100), short, font=f_url, fill=MINT)

    # ---- Optional table-number badge top-right ----
    if table_number is not None:
        f_badge = _font(20, bold=True)
        badge_text = f"СТОЛ №{table_number}"
        bbox = f_badge.getbbox(badge_text)
        bw = bbox[2] - bbox[0] + 36
        bh = 44
        bx = W - pad - bw
        by = pad + 8
        badge = Image.new("RGBA", img.size, (0, 0, 0, 0))
        bd = ImageDraw.Draw(badge)
        bd.rounded_rectangle((bx, by, bx + bw, by + bh), radius=22,
                             fill=(93, 169, 164, 40), outline=MINT, width=2)
        img.alpha_composite(badge)
        draw.text((bx + 18, by + 11), badge_text, font=f_badge, fill=MINT)

    # ---- Tiny "powered by" footer (story only — more space) ----
    if is_story:
        f_pb = _font(18)
        pb = "Powered by REST-MENU"
        bbox = f_pb.getbbox(pb)
        draw.text(((W - (bbox[2] - bbox[0])) // 2, H - 50), pb, font=f_pb, fill=(120, 130, 145))

    out = BytesIO()
    img.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()
