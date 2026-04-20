# Деплой — Личный кабинет ресторана

## Структура

```
├── docker-compose.yml      # Оркестрация всех сервисов
├── deploy.sh               # Скрипт первого запуска
├── .env.example            # Шаблон переменных окружения
├── nginx/
│   └── nginx.conf          # Reverse proxy + SSL
├── backend/
│   ├── Dockerfile
│   └── requirements.prod.txt
└── frontend/
    ├── Dockerfile
    └── nginx-spa.conf      # SPA routing для React
```

## Быстрый старт (VPS)

### 1. Подготовка сервера

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo systemctl enable docker
sudo usermod -aG docker $USER
# Перезайдите в SSH после этого
```

### 2. Клонирование и настройка

```bash
git clone https://github.com/YOUR_USER/YOUR_REPO.git
cd YOUR_REPO

# Копируем и редактируем переменные окружения
cp .env.example .env
nano .env
```

**В `.env` обязательно укажите:**
- `DOMAIN` — ваш домен (например `rest-menu.by`)
- `REACT_APP_BACKEND_URL` — `https://rest-menu.by`
- `JWT_SECRET` — автогенерируется при запуске `deploy.sh`

### 3. Первый запуск

```bash
chmod +x deploy.sh
./deploy.sh
```

Это:
- Генерирует JWT секрет (если не задан)
- Создаёт временный SSL сертификат
- Собирает Docker контейнеры
- Запускает всё

### 4. SSL сертификат (Let's Encrypt)

```bash
# Получить сертификат
docker compose run --rm certbot certonly \
  --webroot -w /var/www/certbot -d rest-menu.by

# Обновить nginx.conf — раскомментировать строки:
#   ssl_certificate /etc/nginx/ssl/live/rest-menu.by/fullchain.pem;
#   ssl_certificate_key /etc/nginx/ssl/live/rest-menu.by/privkey.pem;
# И закомментировать self-signed строки

# Перезапустить nginx
docker compose restart nginx
```

## Управление

```bash
# Статус
docker compose ps

# Логи
docker compose logs -f backend
docker compose logs -f frontend

# Перезапуск
docker compose restart

# Обновление кода
git pull
docker compose build
docker compose up -d

# Бэкап MongoDB
docker compose exec mongo mongodump --out /dump
docker cp $(docker compose ps -q mongo):/dump ./backup_$(date +%Y%m%d)
```

## DNS

Направьте A-запись вашего домена на IP сервера:
```
rest-menu.by → A → 123.45.67.89
```

## Порты

| Сервис | Внутренний | Внешний |
|--------|-----------|---------|
| Nginx  | 80, 443   | 80, 443 |
| Backend | 8001     | —       |
| Frontend | 80      | —       |
| MongoDB | 27017    | —       |

Только nginx открыт наружу. Backend, frontend и MongoDB доступны только внутри Docker-сети.

## MongoDB Atlas (опционально)

Если хотите облачную БД вместо локальной:

1. Создайте кластер на [MongoDB Atlas](https://www.mongodb.com/atlas)
2. В `.env` замените:
   ```
   MONGO_URL=mongodb+srv://user:password@cluster.mongodb.net/restaurant_app
   ```
3. В `docker-compose.yml` удалите сервис `mongo` и `depends_on: mongo`
