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


@router.post("/admin/domains-status/{domain}/renew")
async def renew_domain_cert(domain: str, _: dict = Depends(require_superadmin)):
    """Force-renew Let's Encrypt cert for a specific domain by exec'ing into
    the running certbot container. Requires docker.sock mount.

    Returns stdout/stderr of the certbot run + new cert expiry on success.
    """
    domain = (domain or "").strip().lower()
    if not domain or "/" in domain or ".." in domain:
        raise HTTPException(status_code=400, detail="Некорректный домен")

    if not (SSL_LIVE_DIR / domain / "cert.pem").exists():
        raise HTTPException(status_code=404, detail=f"Сертификат для {domain} не найден (сначала ./scripts/add-domain.sh)")

    try:
        import docker as docker_sdk
    except ImportError:
        raise HTTPException(status_code=500, detail="Библиотека docker не установлена в backend. Пересоберите образ: docker compose build --no-cache backend")

    try:
        client = docker_sdk.from_env()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Нет доступа к docker.sock: {e}. Проверьте mount в docker-compose.yml")

    # Find the certbot container (regardless of project name prefix)
    containers = client.containers.list(filters={"status": "running"})
    certbot_container = None
    for c in containers:
        img = c.image.tags[0] if c.image.tags else ""
        if img.startswith("certbot/certbot") or "certbot" in c.name:
            certbot_container = c
            break

    if not certbot_container:
        raise HTTPException(status_code=500, detail="Контейнер certbot не запущен. docker compose up -d certbot")

    cmd = [
        "certbot", "renew",
        "--force-renewal",
        "--cert-name", domain,
        "--webroot", "-w", "/var/www/certbot",
        "--non-interactive",
    ]
    try:
        exit_code, output = certbot_container.exec_run(cmd, demux=True)
        stdout, stderr = output
        stdout_s = (stdout or b"").decode("utf-8", errors="replace")
        stderr_s = (stderr or b"").decode("utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка запуска certbot: {e}")

    if exit_code != 0:
        # Show tail so user sees actual reason (rate limit / DNS / etc.)
        tail = (stderr_s or stdout_s).strip().splitlines()[-20:]
        raise HTTPException(status_code=500, detail="Certbot вернул ошибку:\n" + "\n".join(tail))

    # Reload nginx to pick up the new cert
    nginx_container = None
    for c in containers:
        img = c.image.tags[0] if c.image.tags else ""
        if img.startswith("nginx") or "nginx" in c.name:
            nginx_container = c
            break
    reload_msg = ""
    if nginx_container:
        try:
            nginx_container.exec_run(["nginx", "-s", "reload"])
            reload_msg = "nginx reloaded"
        except Exception as e:
            reload_msg = f"nginx reload failed: {e}"

    new_cert = _read_cert_expiry(domain)

    return {
        "ok": True,
        "domain": domain,
        "renewed_expires_at": new_cert.get("expires_at"),
        "renewed_days_left": new_cert.get("days_left"),
        "nginx": reload_msg,
        "stdout_tail": "\n".join(stdout_s.strip().splitlines()[-15:]),
    }
