#!/bin/bash
# ============================================================
# Add a custom tenant domain to nginx + auto-issue Let's Encrypt SSL.
# ------------------------------------------------------------
# Usage:
#   ./scripts/add-domain.sh menu.catch.com
#   ./scripts/add-domain.sh menu.catch.com www.menu.catch.com
#
# Prerequisites:
#   1. The domain MUST already point (A-record or CNAME) to this VPS,
#      otherwise Let's Encrypt HTTP-01 challenge will fail.
#   2. Restaurant in admin UI must have this domain added in
#      "Кастомные домены".
#   3. Run from the project root (where docker-compose.yml lives).
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

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${GREEN}▶${NC} $1"; }
warn() { echo -e "${YELLOW}!${NC} $1"; }
err()  { echo -e "${RED}✗${NC} $1"; exit 1; }

# -------- 1. Check nginx.conf already has a block for this domain --------
if grep -q "server_name.*${DOMAIN}" "$NGINX_CONF"; then
    warn "Домен ${DOMAIN} уже есть в nginx.conf. Пропускаю шаг добавления конфига."
else
    log "Добавляю server-блок для ${DOMAIN} в nginx.conf"
    # Insert BEFORE the last closing '}' (end of http {})
    SERVER_BLOCK="
    # ============ Custom tenant domain: ${DOMAIN} ============
    server {
        listen 443 ssl;
        listen [::]:443 ssl;
        server_name ${ALL_DOMAINS};

        ssl_certificate /etc/nginx/ssl/live/${DOMAIN}/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/live/${DOMAIN}/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;

        client_max_body_size 20M;

        location /api/ {
            limit_req zone=api burst=20 nodelay;
            set \$backend_upstream \"backend:8001\";
            proxy_pass http://\$backend_upstream;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
            proxy_set_header X-Forwarded-Host \$host;
            proxy_http_version 1.1;
            proxy_set_header Upgrade \$http_upgrade;
            proxy_set_header Connection \"upgrade\";
            proxy_read_timeout 86400;
        }

        location / {
            set \$frontend_upstream \"frontend:80\";
            proxy_pass http://\$frontend_upstream;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
        }
    }
"
    # Use awk to insert before the final closing brace of the http block
    TMP_FILE=$(mktemp)
    awk -v block="$SERVER_BLOCK" '
        /^}$/ && !inserted { print block; inserted=1 }
        { print }
    ' "$NGINX_CONF" > "$TMP_FILE" && mv "$TMP_FILE" "$NGINX_CONF"
fi

# -------- 2. Get SSL certificate via Let's Encrypt --------
log "Получаю SSL-сертификат Let's Encrypt для ${ALL_DOMAINS}"
DOMAIN_ARGS=""
for d in $ALL_DOMAINS; do DOMAIN_ARGS="$DOMAIN_ARGS -d $d"; done

# Make sure nginx is up so Let's Encrypt can hit /.well-known/acme-challenge/
docker compose up -d nginx

# Run certbot via the certbot container
docker compose run --rm --entrypoint "\
    certbot certonly --webroot -w /var/www/certbot \
    --email admin@${DOMAIN} --agree-tos --no-eff-email \
    $DOMAIN_ARGS" certbot \
    || err "Certbot failed. Проверьте, что DNS-запись ${DOMAIN} указывает на этот сервер."

# -------- 3. Reload nginx with the new config + cert --------
log "Перезапускаю Nginx"
docker compose restart nginx

log "Готово! Домен ${DOMAIN} подключён."
log "Не забудьте в админке добавить ${DOMAIN} в раздел \"Кастомные домены\" нужного ресторана."
