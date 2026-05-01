from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
import uuid
import qrcode
from io import BytesIO
import base64
import os

from database import db
from models import Table, TableCreate
from auth import get_current_user, check_restaurant_access
from helpers import serialize_doc

router = APIRouter()


@router.get("/restaurants/{restaurant_id}/tables")
async def get_tables(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    tables = await db.tables.find({"restaurant_id": restaurant_id}, {"_id": 0}).sort("number", 1).to_list(500)
    return [serialize_doc(t) for t in tables]


@router.post("/restaurants/{restaurant_id}/tables")
async def create_table(restaurant_id: str, data: TableCreate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    table = Table(restaurant_id=restaurant_id, **data.model_dump())
    doc = table.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.tables.insert_one(doc)
    doc.pop('_id', None)
    return doc


@router.put("/restaurants/{restaurant_id}/tables/{table_id}")
async def update_table(restaurant_id: str, table_id: str, data: TableCreate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    await db.tables.update_one({"id": table_id, "restaurant_id": restaurant_id}, {"$set": data.model_dump()})
    return await db.tables.find_one({"id": table_id}, {"_id": 0})


@router.delete("/restaurants/{restaurant_id}/tables/{table_id}")
async def delete_table(restaurant_id: str, table_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    await db.tables.delete_one({"id": table_id, "restaurant_id": restaurant_id})
    return {"message": "Table deleted"}


@router.post("/restaurants/{restaurant_id}/tables/{table_id}/regenerate-code")
async def regenerate_table_code(restaurant_id: str, table_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    new_code = str(uuid.uuid4())[:8].upper()
    await db.tables.update_one({"id": table_id, "restaurant_id": restaurant_id}, {"$set": {"code": new_code}})
    return {"code": new_code}


@router.get("/restaurants/{restaurant_id}/tables/{table_id}/qr")
async def get_table_qr(restaurant_id: str, table_id: str, base_url: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    table = await db.tables.find_one({"id": table_id, "restaurant_id": restaurant_id}, {"_id": 0})
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    if not base_url:
        base_url = os.environ.get('FRONTEND_URL', 'https://example.com')

    # Use slug-based URL if restaurant has a slug
    restaurant = await db.restaurants.find_one({"id": restaurant_id}, {"_id": 0})
    slug = restaurant.get('slug', '') if restaurant else ''

    if slug:
        menu_url = f"{base_url}/{slug}/{table['number']}"
    else:
        menu_url = f"{base_url}/menu/{table['code']}"

    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=2)
    qr.add_data(menu_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return {
        "table_id": table_id,
        "table_number": table['number'],
        "table_code": table['code'],
        "menu_url": menu_url,
        "qr_base64": f"data:image/png;base64,{img_base64}"
    }


@router.get("/restaurants/{restaurant_id}/tables/{table_id}/qr-pdf")
async def get_table_qr_pdf(
    restaurant_id: str,
    table_id: str,
    base_url: Optional[str] = None,
    size: str = "a5",
    current_user: dict = Depends(get_current_user),
):
    """Generate a print-ready PDF for a table QR-code.

    size: 'a5' (default, full A5 page) or 'a6' (A6 page, fits in stand).
    """
    from reportlab.pdfgen import canvas as rl_canvas

    await check_restaurant_access(current_user, restaurant_id)
    table = await db.tables.find_one({"id": table_id, "restaurant_id": restaurant_id}, {"_id": 0})
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    restaurant = await db.restaurants.find_one({"id": restaurant_id}, {"_id": 0})
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    base_url = (base_url or os.environ.get('FRONTEND_URL', 'https://example.com')).rstrip("/")

    page_size = _qr_page_size(size)
    pdf_buf = BytesIO()
    c = rl_canvas.Canvas(pdf_buf, pagesize=page_size)
    fonts = _qr_register_fonts()
    logo_reader = await _qr_load_logo_reader(restaurant.get('logo_url'))
    await _qr_draw_page(c, page_size, restaurant, table, base_url, size, fonts, logo_reader)
    c.showPage()
    c.save()
    pdf_buf.seek(0)

    filename = f"qr_table_{table.get('number', '?')}_{size.lower()}.pdf"
    return StreamingResponse(
        pdf_buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/restaurants/{restaurant_id}/tables/qr-pdf-all")
async def get_all_tables_qr_pdf(
    restaurant_id: str,
    base_url: Optional[str] = None,
    size: str = "a5",
    current_user: dict = Depends(get_current_user),
):
    """Generate a single multi-page PDF with QR-codes for ALL active tables of
    a restaurant. One table per page, A5 or A6.
    """
    from reportlab.pdfgen import canvas as rl_canvas

    await check_restaurant_access(current_user, restaurant_id)
    restaurant = await db.restaurants.find_one({"id": restaurant_id}, {"_id": 0})
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    tables = await db.tables.find(
        {"restaurant_id": restaurant_id, "is_active": True}, {"_id": 0}
    ).sort("number", 1).to_list(500)
    if not tables:
        raise HTTPException(status_code=404, detail="У ресторана нет активных столов")

    base_url = (base_url or os.environ.get('FRONTEND_URL', 'https://example.com')).rstrip("/")

    page_size = _qr_page_size(size)
    pdf_buf = BytesIO()
    c = rl_canvas.Canvas(pdf_buf, pagesize=page_size)
    fonts = _qr_register_fonts()
    # Load logo once — reused on every page.
    logo_reader = await _qr_load_logo_reader(restaurant.get('logo_url'))

    for table in tables:
        await _qr_draw_page(c, page_size, restaurant, table, base_url, size, fonts, logo_reader)
        c.showPage()

    c.save()
    pdf_buf.seek(0)

    safe_name = (restaurant.get('slug') or restaurant_id)[:40]
    filename = f"qr_all_{safe_name}_{size.lower()}.pdf"
    return StreamingResponse(
        pdf_buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ============ QR PDF helpers ============

def _qr_page_size(size: str):
    from reportlab.lib.pagesizes import A5, A6
    return A6 if (size or "").lower() == "a6" else A5


def _qr_register_fonts():
    """Register DejaVu fonts (with Cyrillic) once. Returns dict {regular,bold}."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font_name = "Helvetica"
    font_bold = "Helvetica-Bold"
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    ):
        if os.path.exists(path):
            try:
                if "DejaVu" not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont("DejaVu", path))
                font_name = "DejaVu"
                bold_path = path.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf")
                if os.path.exists(bold_path):
                    if "DejaVu-Bold" not in pdfmetrics.getRegisteredFontNames():
                        pdfmetrics.registerFont(TTFont("DejaVu-Bold", bold_path))
                    font_bold = "DejaVu-Bold"
                break
            except Exception:
                pass
    return {"regular": font_name, "bold": font_bold}


async def _qr_load_logo_reader(logo_url: Optional[str]):
    """Download a remote logo into memory once. Returns ImageReader or None."""
    from reportlab.lib.utils import ImageReader
    import httpx

    url = (logo_url or "").strip()
    if not url or not url.startswith("http"):
        return None
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return None
            return ImageReader(BytesIO(r.content))
    except Exception:
        return None


async def _qr_draw_page(c, page_size, restaurant, table, base_url, size, fonts, logo_reader):
    """Render a single QR page on the provided ReportLab canvas."""
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader

    width, height = page_size
    is_a6 = (size or "").lower() == "a6"

    slug = (restaurant.get('slug') or '').strip()
    if slug:
        menu_url = f"{base_url}/{slug}/{table['number']}"
    else:
        menu_url = f"{base_url}/menu/{table['code']}"

    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=2)
    qr.add_data(menu_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#1a1a1a", back_color="white").convert("RGB")
    qr_buf = BytesIO()
    qr_img.save(qr_buf, format="PNG")
    qr_buf.seek(0)
    qr_reader = ImageReader(qr_buf)

    restaurant_name = restaurant.get('name', '') or ''
    table_number = table.get('number', '?')
    accent = "#5DA9A4"  # mint, matches admin UI

    # ---------- Background frame ----------
    margin = 8 * mm
    c.setStrokeColor(accent)
    c.setLineWidth(1.2)
    c.roundRect(margin, margin, width - 2 * margin, height - 2 * margin, 6 * mm, stroke=1, fill=0)

    # ---------- Top: logo + restaurant name ----------
    cursor_y = height - margin - 12 * mm
    if logo_reader is not None:
        try:
            iw, ih = logo_reader.getSize()
            target_h = 14 * mm
            target_w = target_h * (iw / ih)
            c.drawImage(logo_reader, (width - target_w) / 2, cursor_y - target_h,
                        width=target_w, height=target_h, mask='auto')
            cursor_y -= target_h + 3 * mm
        except Exception:
            pass

    if restaurant_name:
        c.setFont(fonts["bold"], 16 if is_a6 else 20)
        c.setFillColor("#1a1a1a")
        c.drawCentredString(width / 2, cursor_y, restaurant_name)
        cursor_y -= 8 * mm

    # ---------- Headline ----------
    c.setFont(fonts["regular"], 10 if is_a6 else 12)
    c.setFillColor("#666666")
    c.drawCentredString(width / 2, cursor_y, "Отсканируйте код, чтобы открыть меню")
    cursor_y -= 6 * mm

    # ---------- QR code ----------
    qr_size = (62 * mm) if is_a6 else (90 * mm)
    qr_x = (width - qr_size) / 2
    qr_y = cursor_y - qr_size
    pad = 4 * mm
    c.setFillColor("white")
    c.setStrokeColor("#e5e7eb")
    c.setLineWidth(0.6)
    c.roundRect(qr_x - pad, qr_y - pad, qr_size + 2 * pad, qr_size + 2 * pad, 3 * mm, stroke=1, fill=1)
    c.drawImage(qr_reader, qr_x, qr_y, width=qr_size, height=qr_size, preserveAspectRatio=True, mask='auto')
    cursor_y = qr_y - pad - 6 * mm

    # ---------- Table number ----------
    c.setFont(fonts["bold"], 22 if is_a6 else 28)
    c.setFillColor(accent)
    c.drawCentredString(width / 2, cursor_y - 8 * mm, f"Стол №{table_number}")

    # ---------- Footer (small URL) ----------
    c.setFont(fonts["regular"], 7)
    c.setFillColor("#9ca3af")
    c.drawCentredString(width / 2, margin + 4 * mm, menu_url)
