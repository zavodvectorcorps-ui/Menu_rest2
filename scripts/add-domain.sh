#!/bin/bash
# ============================================================
# Add a custom tenant domain to nginx + auto-issue Let's Encrypt SSL.
# ------------------------------------------------------------
# Usage:
#   ./scripts/add-domain.sh menu.catch.com
#   ./scripts/add-domain.sh menu.catch.com www.menu.catch.com
#
# What it does:
#   1. Verifies that DNS A-record of the domain points to THIS server.
#      If not — exits early with a clear error (no point asking certbot).
#   2. Adds an HTTPS server-block to nginx/nginx.conf (idempotent — skips
#      if the block already exists).
#   3. Issues a Let's Encrypt certificate via the certbot container.
#   4. Reloads nginx so the new domain is picked up.
#
# Prerequisites:
#   - Run from the project root (where docker-compose.yml lives).
#   - The client must have already pointed the domain (A-record OR CNAME) to
#     this VPS. DNS propagation usually takes 5–30 minutes.
#   - In admin panel («Модули ресторанов» → «Кастомные домены») the same
#     domain must be added to the target restaurant. Otherwise the menu
#     endpoint won't know which restaurant the domain belongs to.
# ============================================================

set -e

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <domain> [extra_domain ...]"
    echo "Example: $0 menu.catch.com"
    exit 1
fi

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

NGINX_CONF="$PROJECT_DIR/nginx/nginx.conf"
DOMAIN="$1"
shift
EXTRA_DOMAINS="$@"
ALL_DOMAINS="$DOMAIN $EXTRA_DOMAINS"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BLUE='\033[0;34m'; NC='\033[0m'
log()  { echo -e "${BLUE}▶${NC} $1"; }
ok()   { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}!${NC} $1"; }
err()  { echo -e "${RED}✗${NC} $1"; exit 1; }

# -------- 0. Verify DNS points to this server --------
log "Проверяю DNS-запись для ${DOMAIN}..."
SERVER_IP=$(curl -fsS --max-time 5 https://api.ipify.org 2>/dev/null || \
            curl -fsS --max-time 5 https://ifconfig.me 2>/dev/null || \
            hostname -I | awk '{print $1}')
if [ -z "$SERVER_IP" ]; then
    warn "Не удалось определить публичный IP сервера. Пропускаю DNS-проверку."
else
    log "Публичный IP сервера: ${SERVER_IP}"
    DOMAIN_IPS=$(getent ahosts "$DOMAIN" 2>/dev/null | awk '{print $1}' | sort -u | tr '\n' ' ')
    if [ -z "$DOMAIN_IPS" ]; then
        err "DNS не отвечает для ${DOMAIN}. Создайте у регистратора A-запись: ${DOMAIN} → ${SERVER_IP} и подождите 5-30 минут."
    fi
    log "DNS вернул: ${DOMAIN_IPS}"
    if ! echo "$DOMAIN_IPS" | grep -qw "$SERVER_IP"; then
        err "Домен ${DOMAIN} указывает на ${DOMAIN_IPS}, а сервер имеет IP ${SERVER_IP}. Поправьте A-запись и подождите DNS-пропагацию."
    fi
    ok "DNS корректно указывает на этот сервер"
fi

# -------- 1. Add nginx server-block (idempotent) --------
if grep -qE "server_name[^;]*\b${DOMAIN}\b" "$NGINX_CONF"; then
    warn "Домен ${DOMAIN} уже есть в nginx.conf. Пропускаю шаг добавления конфига."
else
    log "Добавляю server-блок для ${DOMAIN} в nginx.conf"
    SERVER_BLOCK=$(cat <<'BLOCK_EOF'

    # ============ Custom tenant domain: __DOMAIN__ ============
    server {
        listen 443 ssl;
        listen [::]:443 ssl;
        server_name __ALL_DOMAINS__;

        ssl_certificate /etc/nginx/ssl/live/__DOMAIN__/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/live/__DOMAIN__/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;

        client_max_body_size 20M;

        location /api/ {
            limit_req zone=api burst=20 nodelay;
            set $backend_upstream "backend:8001";
            proxy_pass http://$backend_upstream;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 86400;
        }

        location / {
            set $frontend_upstream "frontend:80";
            proxy_pass http://$frontend_upstream;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
BLOCK_EOF
)
    SERVER_BLOCK=${SERVER_BLOCK//__DOMAIN__/$DOMAIN}
    SERVER_BLOCK=${SERVER_BLOCK//__ALL_DOMAINS__/$ALL_DOMAINS}

    # Insert before the LAST closing '}' of the file (which is the closer of
    # the http {} block). Naive "first ^}$ wins" inserts after events {} —
    # that's how rest-menu.by went down on 2026-05-02.
    BLOCK_FILE=$(mktemp)
    printf '%s\n' "$SERVER_BLOCK" > "$BLOCK_FILE"
    TMP_FILE=$(mktemp)
    python3 - "$NGINX_CONF" "$TMP_FILE" "$BLOCK_FILE" <<'PYEOF'
import sys, pathlib
src = pathlib.Path(sys.argv[1]).read_text().splitlines(keepends=True)
block = pathlib.Path(sys.argv[3]).read_text()
last_close = max(i for i, line in enumerate(src) if line.rstrip() == "}")
src.insert(last_close, block if block.endswith("\n") else block + "\n")
pathlib.Path(sys.argv[2]).write_text("".join(src))
PYEOF
    rm -f "$BLOCK_FILE"
    mv "$TMP_FILE" "$NGINX_CONF"
    # Validate config syntax before restarting nginx — fail fast if broken.
    if ! docker run --rm -v "$NGINX_CONF":/etc/nginx/nginx.conf:ro nginx:alpine nginx -t -c /etc/nginx/nginx.conf >/dev/null 2>&1; then
        warn "Конфиг nginx после вставки невалиден — откатываюсь к git."
        git checkout HEAD -- "$NGINX_CONF" 2>/dev/null || true
        err "Не удалось безопасно вставить server-блок. nginx.conf откачен."
    fi
    ok "Server-блок добавлен и проверен (nginx -t)"
fi

# -------- 2. Make sure nginx is up so certbot HTTP-01 challenge works --------
log "Поднимаю nginx (для ACME challenge)"
docker compose up -d nginx >/dev/null

# -------- 3. Issue Let's Encrypt certificate --------
DOMAIN_ARGS=""
for d in $ALL_DOMAINS; do DOMAIN_ARGS="$DOMAIN_ARGS -d $d"; done

if [ -d "$PROJECT_DIR/nginx/ssl/live/$DOMAIN" ]; then
    warn "Сертификат для ${DOMAIN} уже существует. Пропускаю выпуск."
else
    log "Получаю SSL-сертификат Let's Encrypt для ${ALL_DOMAINS}"
    docker compose run --rm --entrypoint "\
        certbot certonly --webroot -w /var/www/certbot \
        --email admin@${DOMAIN} --agree-tos --no-eff-email \
        $DOMAIN_ARGS" certbot \
        || err "Certbot failed. Возможные причины: DNS не указывает на этот сервер, порт 80 закрыт, или Let's Encrypt rate limit."
    ok "Сертификат получен"
fi

# -------- 4. Reload nginx --------
log "Перезапускаю Nginx"
docker compose restart nginx >/dev/null

ok "Готово! Домен ${DOMAIN} подключён."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Что проверить:"
echo "  1. Откройте https://${DOMAIN}/api/health — должен вернуть {\"status\":\"ok\"}"
echo "  2. В админке нажмите «Проверить» рядом с этим доменом"
echo "  3. Откройте QR-код стола — он автоматически использует новый домен"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
