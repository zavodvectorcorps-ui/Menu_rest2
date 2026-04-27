# Полная инструкция: перенос проекта на свой VPS

## Что переносим
| Компонент | Размер | Ссылка для скачивания |
|-----------|--------|----------------------|
| Исходный код | — | GitHub (уже есть) |
| База данных (17 коллекций) | 86 KB | `https://margin-control-4.preview.emergentagent.com/api/db-backup/download` |
| Картинки блюд (1019 шт) | 89 MB | `https://margin-control-4.preview.emergentagent.com/api/uploads-backup/download` |

---

## Шаг 1. Подготовка VPS

### 1.1 Арендовать сервер
- **Hetzner** (Финляндия/Германия) — от 4€/мес, CX22 (2 vCPU, 4GB RAM) хватит
- **DigitalOcean** — от $6/мес
- Минимум: 2GB RAM, 20GB диск, Ubuntu 22.04

### 1.2 Подключиться и установить Docker
```bash
ssh root@ВАШ_IP

# Обновить систему
apt update && apt upgrade -y

# Установить Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker

# Установить Docker Compose
apt install -y docker-compose-plugin

# Установить MongoDB Tools (для восстановления дампа)
apt install -y mongodb-database-tools

# Проверка
docker --version
docker compose version
```

---

## Шаг 2. Скачать всё на сервер

```bash
# Создать директорию проекта
mkdir -p /opt/restaurant && cd /opt/restaurant

# 2.1 Клонировать код из GitHub
git clone https://github.com/ВАШ_USER/ВАШ_REPO.git .

# 2.2 Скачать дамп базы данных
curl -o db_backup.tar.gz https://margin-control-4.preview.emergentagent.com/api/db-backup/download

# 2.3 Скачать картинки блюд
curl -o uploads_backup.tar.gz https://margin-control-4.preview.emergentagent.com/api/uploads-backup/download

# Проверить размеры (БД ~86KB, картинки ~89MB)
ls -lh db_backup.tar.gz uploads_backup.tar.gz
```

---

## Шаг 3. Настроить переменные окружения

```bash
# Скопировать шаблон
cp env.example .env

# Редактировать
nano .env
```

**Заполнить в `.env`:**
```
DOMAIN=rest-menu.by
REACT_APP_BACKEND_URL=https://rest-menu.by
JWT_SECRET=<сгенерируйте: openssl rand -hex 32>
CORS_ORIGINS=https://rest-menu.by
```

---

## Шаг 4. Первый запуск

```bash
# Сделать скрипт исполняемым
chmod +x deploy.sh

# Запустить (создаст SSL, соберёт контейнеры, запустит)
./deploy.sh
```

Дождитесь завершения сборки (3-5 минут). Проверка:
```bash
docker compose ps
# Все сервисы должны быть "Up"
```

---

## Шаг 5. Восстановить базу данных

```bash
# 5.1 Распаковать дамп
tar -xzf db_backup.tar.gz

# 5.2 Скопировать в контейнер MongoDB
docker cp mongodump_binary $(docker compose ps -q mongo):/tmp/

# 5.3 Восстановить (исходная БД: test_database → новая: restaurant_app)
docker compose exec mongo mongorestore \
  --db restaurant_app \
  /tmp/mongodump_binary/test_database

# 5.4 Проверить
docker compose exec mongo mongosh restaurant_app --eval "db.getCollectionNames()"
# Должно показать 17 коллекций
```

---

## Шаг 6. Восстановить картинки

```bash
# 6.1 Распаковать
tar -xzf uploads_backup.tar.gz

# 6.2 Скопировать в контейнер бэкенда
docker cp uploads $(docker compose ps -q backend):/app/

# 6.3 Проверить
docker compose exec backend ls /app/uploads | wc -l
# Должно показать 1019
```

---

## Шаг 7. Настроить DNS

В панели управления доменом `rest-menu.by`:
```
Тип: A
Имя: @
Значение: IP_ВАШЕГО_VPS
TTL: 300
```

Подождите 5-30 минут на распространение DNS:
```bash
dig rest-menu.by +short
# Должен показать ваш IP
```

---

## Шаг 8. Получить SSL сертификат (Let's Encrypt)

```bash
# 8.1 Получить сертификат
docker compose run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d rest-menu.by \
  --email ваш@email.com \
  --agree-tos

# 8.2 Обновить nginx конфиг
nano nginx/nginx.conf
```

В `nginx/nginx.conf` замените:
```nginx
# Закомментировать:
# ssl_certificate /etc/nginx/ssl/selfsigned.crt;
# ssl_certificate_key /etc/nginx/ssl/selfsigned.key;

# Раскомментировать и подставить домен:
ssl_certificate /etc/nginx/ssl/live/rest-menu.by/fullchain.pem;
ssl_certificate_key /etc/nginx/ssl/live/rest-menu.by/privkey.pem;
```

```bash
# 8.3 Перезапустить nginx
docker compose restart nginx
```

---

## Шаг 9. Проверка

```bash
# Открыть в браузере:
https://rest-menu.by/login
# Войти: admin / 220066

# Проверить API:
curl -s https://rest-menu.by/api/auth/login \
  -X POST -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"220066"}' | head -c 100

# Проверить картинки:
curl -s -o /dev/null -w "%{http_code}" https://rest-menu.by/api/uploads/ЛЮБОЙ_ФАЙЛ.jpg
```

---

## Управление после деплоя

```bash
# Логи
docker compose logs -f backend    # бэкенд
docker compose logs -f frontend   # фронтенд
docker compose logs -f nginx      # прокси

# Перезапуск
docker compose restart

# Обновление кода
cd /opt/restaurant
git pull
docker compose build
docker compose up -d

# Бэкап базы
docker compose exec mongo mongodump --db restaurant_app --out /tmp/backup
docker cp $(docker compose ps -q mongo):/tmp/backup ./backup_$(date +%Y%m%d)

# Просмотр статуса
docker compose ps
```

---

## Устранение проблем

### Сайт не открывается
```bash
docker compose ps          # все ли контейнеры Up?
docker compose logs nginx  # ошибки прокси
```

### 502 Bad Gateway
```bash
docker compose logs backend  # ошибки бэкенда
docker compose restart backend
```

### Картинки не загружаются
```bash
docker compose exec backend ls /app/uploads | wc -l  # файлы на месте?
```

### SSL не работает
```bash
docker compose logs certbot
# Убедитесь что DNS уже указывает на ваш IP
```
