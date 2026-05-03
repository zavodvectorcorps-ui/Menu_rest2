#!/bin/bash
# Remove a custom tenant domain: deletes per-domain nginx config and reloads.
# Сертификат (nginx/ssl/live/DOMAIN/) остаётся на случай возврата домена.
# Usage: ./scripts/remove-domain.sh catch-menu.by

set -e

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <domain>"; exit 1
fi

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

DOMAIN="$1"
CUSTOM_DIR="$PROJECT_DIR/nginx/custom-domains"
DOMAIN_CONF="$CUSTOM_DIR/${DOMAIN}.conf"

if [ ! -f "$DOMAIN_CONF" ]; then
    echo "Конфиг ${DOMAIN_CONF} не найден. Текущие активные домены:"
    ls -1 "$CUSTOM_DIR"/*.conf 2>/dev/null | xargs -n1 basename -s .conf 2>/dev/null || echo "  (пусто)"
    exit 1
fi

rm "$DOMAIN_CONF"
echo "✓ Удалил $DOMAIN_CONF"

docker compose restart nginx >/dev/null
echo "✓ Nginx перезапущен"
echo ""
echo "Домен ${DOMAIN} отключён. Сертификат остался в nginx/ssl/live/${DOMAIN}/ (можно удалить вручную)."
