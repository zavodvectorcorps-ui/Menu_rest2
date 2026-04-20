#!/bin/bash
set -e

# ============================
# Скрипт первого запуска
# rest-menu.by deployment
# ============================

echo "=== Настройка сервера ==="

# 1. Проверка .env
if [ ! -f .env ]; then
    echo "Создаю .env из примера..."
    cp .env.example .env
    # Генерация JWT секрета
    JWT=$(openssl rand -hex 32)
    sed -i "s/CHANGE_ME_GENERATE_RANDOM_SECRET/$JWT/" .env
    echo "ВАЖНО: Отредактируйте .env — укажите ваш домен!"
    echo "  nano .env"
    exit 1
fi

source .env

# 2. Создание директории для SSL
mkdir -p nginx/ssl

# 3. Генерация временного self-signed сертификата (для первого запуска)
if [ ! -f nginx/ssl/selfsigned.crt ]; then
    echo "Генерирую временный SSL сертификат..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout nginx/ssl/selfsigned.key \
        -out nginx/ssl/selfsigned.crt \
        -subj "/CN=$DOMAIN"
fi

# 4. Сборка и запуск
echo "=== Сборка Docker контейнеров ==="
docker compose build

echo "=== Запуск ==="
docker compose up -d

echo ""
echo "=== Готово! ==="
echo "Сайт доступен: https://$DOMAIN"
echo ""
echo "Следующий шаг — получить SSL от Let's Encrypt:"
echo "  docker compose run --rm certbot certonly --webroot -w /var/www/certbot -d $DOMAIN"
echo "  Затем обновите nginx/nginx.conf — раскомментируйте строки ssl_certificate"
echo "  docker compose restart nginx"
