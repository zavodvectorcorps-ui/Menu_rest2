#!/bin/bash
# ============================================================
# Single-command update deployment for rest-menu.by on VPS
# ------------------------------------------------------------
# Usage:
#   ./update.sh              — умное обновление (git pull + пересборка только изменённых сервисов)
#   ./update.sh --full       — полная пересборка всех сервисов без кеша
#   ./update.sh --frontend   — пересобрать только frontend
#   ./update.sh --backend    — пересобрать только backend
#   ./update.sh --no-pull    — пропустить git pull (деплой локальных изменений)
# ============================================================

set -e

# Enable BuildKit for fast parallel builds + layer cache
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# -------- Colors --------
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${BLUE}▶${NC}  $1"; }
ok()   { echo -e "${GREEN}✓${NC}  $1"; }
warn() { echo -e "${YELLOW}!${NC}  $1"; }
err()  { echo -e "${RED}✗${NC}  $1"; }

# -------- Parse args --------
MODE="smart"
PULL=true
for arg in "$@"; do
    case $arg in
        --full)     MODE="full";     ;;
        --frontend) MODE="frontend"; ;;
        --backend)  MODE="backend";  ;;
        --no-pull)  PULL=false;      ;;
        -h|--help)
            grep -E "^#" "$0" | head -20; exit 0 ;;
        *) warn "Неизвестный аргумент: $arg" ;;
    esac
done

START_TIME=$(date +%s)

# -------- Step 1. Pull latest code --------
if [ "$PULL" = true ]; then
    log "Обновляю код из GitHub (git pull)..."
    BEFORE=$(git rev-parse HEAD)
    git pull --ff-only
    AFTER=$(git rev-parse HEAD)
    if [ "$BEFORE" = "$AFTER" ]; then
        ok "Код уже актуален ($(git rev-parse --short HEAD))"
    else
        ok "Обновлено: $(git rev-parse --short $BEFORE) → $(git rev-parse --short $AFTER)"
    fi
else
    warn "Пропущен git pull (--no-pull)"
    BEFORE=""
    AFTER=""
fi

# -------- Step 2. Detect what changed --------
REBUILD_FRONTEND=false
REBUILD_BACKEND=false
NO_CACHE=""

case "$MODE" in
    full)
        REBUILD_FRONTEND=true
        REBUILD_BACKEND=true
        NO_CACHE="--no-cache"
        warn "Режим: FULL rebuild без кеша"
        ;;
    frontend)
        REBUILD_FRONTEND=true
        log "Режим: пересборка только frontend"
        ;;
    backend)
        REBUILD_BACKEND=true
        log "Режим: пересборка только backend"
        ;;
    smart)
        if [ -n "$BEFORE" ] && [ "$BEFORE" != "$AFTER" ]; then
            CHANGED=$(git diff --name-only "$BEFORE" "$AFTER")
            echo "$CHANGED" | grep -q "^frontend/" && REBUILD_FRONTEND=true || true
            echo "$CHANGED" | grep -q "^backend/"  && REBUILD_BACKEND=true  || true
            if [ "$REBUILD_FRONTEND" = false ] && [ "$REBUILD_BACKEND" = false ]; then
                ok "В коде нет изменений backend/frontend. Нечего пересобирать."
                # Still restart to apply any compose/nginx/.env changes
                if echo "$CHANGED" | grep -qE "^(docker-compose\.yml|nginx/|\.env)"; then
                    warn "Обнаружены изменения инфраструктуры — перезапускаю контейнеры"
                    docker compose up -d
                fi
                exit 0
            fi
        else
            # No git pull or no new commits — rebuild frontend by default
            warn "Нет git-дифа — пересобираю frontend по умолчанию"
            REBUILD_FRONTEND=true
        fi
        ;;
esac

# -------- Step 3. Build changed services --------
SERVICES=()
[ "$REBUILD_FRONTEND" = true ] && SERVICES+=("frontend")
[ "$REBUILD_BACKEND" = true ]  && SERVICES+=("backend")

log "Пересобираю: ${SERVICES[*]}"
docker compose build $NO_CACHE "${SERVICES[@]}"
ok "Сборка завершена"

# -------- Step 4. Recreate only changed services (zero-downtime) --------
log "Перезапускаю сервисы..."
docker compose up -d --no-deps "${SERVICES[@]}"
ok "Сервисы перезапущены"

# -------- Step 5. Cleanup dangling images (save disk space) --------
log "Очистка неиспользуемых образов..."
docker image prune -f >/dev/null
ok "Очистка завершена"

# -------- Step 6. Health check --------
sleep 3
log "Статус контейнеров:"
docker compose ps

ELAPSED=$(( $(date +%s) - START_TIME ))
echo ""
ok "Деплой завершён за ${ELAPSED} сек"
echo ""
echo "Логи в реальном времени:  docker compose logs -f --tail=50"
