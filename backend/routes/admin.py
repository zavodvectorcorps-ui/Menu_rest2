"""Administrative endpoints: VPS-wide domain/cert overview for superadmins."""
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException

from database import db
from auth import require_superadmin

router = APIRouter()

CUSTOM_DOMAINS_DIR = Path("/etc/nginx/custom-domains")
SSL_LIVE_DIR = Path("/etc/nginx/ssl/live")


def _read_cert_expiry(domain: str) -> dict:
    """Return {expires_at: ISO-8601 str, days_left: int, error: None|str}.

    Reads `/etc/nginx/ssl/live/{domain}/cert.pem`. Directory missing = no cert.
    """
    cert_path = SSL_LIVE_DIR / domain / "cert.pem"
    if not cert_path.exists():
        return {"expires_at": None, "days_left": None, "error": "no_cert"}
    try:
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend

        raw = cert_path.read_bytes()
        cert = x509.load_pem_x509_certificate(raw, default_backend())
        # not_valid_after_utc (Python 3.12+) или not_valid_after (deprecated)
        try:
            expires = cert.not_valid_after_utc
        except AttributeError:
            expires = cert.not_valid_after.replace(tzinfo=timezone.utc)
        days_left = (expires - datetime.now(timezone.utc)).days
        return {"expires_at": expires.isoformat(), "days_left": days_left, "error": None}
    except Exception as e:
        return {"expires_at": None, "days_left": None, "error": f"parse_error: {e}"}


@router.get("/admin/domains-status")
async def get_domains_status(_: dict = Depends(require_superadmin)):
    """Unified view of all custom tenant domains on this VPS.

    Cross-references three data sources:
      1. Files in /etc/nginx/custom-domains/*.conf (nginx configs)
      2. Restaurant.custom_domains in MongoDB
      3. Let's Encrypt certs in /etc/nginx/ssl/live/<domain>/cert.pem

    Each row has `overall` status: ok | warning | error, plus diagnostics.
    """
    # 1. Collect nginx-config domains
    config_domains = set()
    if CUSTOM_DOMAINS_DIR.exists():
        for p in CUSTOM_DOMAINS_DIR.glob("*.conf"):
            # filename without .conf = domain
            config_domains.add(p.stem.lower())

    # 2. Collect DB domains + owner restaurants
    restaurants = await db.restaurants.find(
        {"custom_domains": {"$exists": True, "$ne": []}},
        {"_id": 0, "id": 1, "name": 1, "custom_domains": 1, "slug": 1},
    ).to_list(500)
    db_map = {}  # {domain_lower: {id, name, slug}}
    for r in restaurants:
        for d in (r.get("custom_domains") or []):
            key = (d or "").strip().lower()
            if key:
                db_map[key] = {"id": r["id"], "name": r.get("name", ""), "slug": r.get("slug", "")}

    # 3. Union of all known domains
    all_domains = sorted(config_domains | set(db_map.keys()))

    rows = []
    for domain in all_domains:
        has_config = domain in config_domains
        owner = db_map.get(domain)
        cert = _read_cert_expiry(domain)

        # Verdict
        if not has_config and owner:
            overall = "error"
            summary = "Домен привязан к ресторану в админке, но на VPS не настроен. Запустите ./scripts/add-domain.sh " + domain
        elif has_config and not owner:
            overall = "warning"
            summary = "Nginx настроен, но ни один ресторан не заявляет этот домен. Удалите через ./scripts/remove-domain.sh или добавьте в админке."
        elif cert.get("error") == "no_cert":
            overall = "error"
            summary = "Нет SSL-сертификата. Запустите ./scripts/add-domain.sh " + domain
        elif cert.get("error"):
            overall = "warning"
            summary = f"Не удалось прочитать сертификат: {cert['error']}"
        elif cert.get("days_left") is not None and cert["days_left"] < 7:
            overall = "warning"
            summary = f"Сертификат истекает через {cert['days_left']} дн. Обычно certbot продлевает автоматически."
        else:
            overall = "ok"
            summary = f"Работает. Сертификат до {cert['expires_at'][:10] if cert.get('expires_at') else '—'}."

        rows.append({
            "domain": domain,
            "has_nginx_config": has_config,
            "owner_restaurant": owner,
            "cert": cert,
            "overall": overall,
            "summary": summary,
        })

    return {
        "total": len(rows),
        "custom_domains_dir": str(CUSTOM_DOMAINS_DIR),
        "dir_exists": CUSTOM_DOMAINS_DIR.exists(),
        "rows": rows,
    }
