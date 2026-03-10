# PRD: Личный кабинет ресторана

## Дата создания: 2026-01-26
## Последнее обновление: 2026-03-10

## Оригинальное ТЗ
Веб-приложение "Личный кабинет ресторана" по типу LunchPad. Админка + клиентское меню по QR-коду.

## Архитектура

### Бэкенд (FastAPI + MongoDB)
```
/app/backend/
├── server.py          # Точка входа (62 строки)
├── database.py        # MongoDB подключение
├── models.py          # Все Pydantic модели
├── auth.py            # JWT, пароли, проверка доступа
├── helpers.py         # serialize_doc, seed, get_or_create_*
├── services/
│   ├── telegram.py    # Отправка в Telegram
│   ├── images.py      # Скачивание изображений
│   └── websocket.py   # ConnectionManager для WS
├── routes/
│   ├── auth.py        # login, me, users CRUD
│   ├── restaurants.py # рестораны CRUD
│   ├── menu.py        # секции, категории, позиции, ярлыки, импорт
│   ├── tables.py      # столы, QR-коды
│   ├── orders.py      # заказы, вызовы, complete-all
│   ├── settings.py    # настройки, сотрудники, аналитика
│   ├── public.py      # публичное меню, заказы, вызовы + WS broadcast
│   ├── telegram.py    # управление Telegram-ботом
│   ├── ws.py          # WebSocket endpoint
│   └── seed.py        # health, seed
```

### Фронтенд (React + Tailwind)
```
/app/frontend/src/
├── hooks/
│   └── useWebSocket.js         # WS hook с reconnect/ping
├── components/menu/
│   ├── ImageUpload.jsx
│   ├── SortableCategoryItem.jsx
│   ├── SortableMenuItem.jsx
│   └── MenuDialogs.jsx
├── pages/
│   ├── AdminLayout.jsx         # Глобальные WS уведомления + индикатор
│   ├── MenuPage.jsx
│   ├── OrdersPage.jsx          # Авто-обновление по WS
│   ├── ClientMenuPage.jsx
│   └── ...
```

## Реализовано

### Мультитенантность и авторизация
- JWT, роли суперадмин/менеджер

### Telegram-бот, импорт меню (.data/.json), ярлыки, предзаказы

### Массовое завершение заказов/вызовов

### WebSocket уведомления в реальном времени (2026-03-10)
- WS endpoint: /api/ws/{restaurant_id}?token={jwt}
- Broadcast new_order и new_staff_call при создании через публичный API
- Глобальные toast-уведомления на всех страницах админки
- Звуковое уведомление (AudioContext, включение/выключение в localStorage)
- Индикатор подключения в сайдбаре (зелёная/красная точка)
- Auto-refresh списка заказов на OrdersPage
- Auto-reconnect через 3 сек, ping каждые 30 сек

### Рефакторинг (2026-03-10)
- server.py: 1936 → 62 строки (16 модулей)
- MenuPage.jsx: 1402 → 477 строк (4 компонента)

## Учётные данные
- Суперадмин: admin / 220066
- Рестораны: Мята Спортивная (aa25189d), Catch (d433dc80)

## Бэклог
- P1: Интеграция с Caffesta POS (ожидает API-документацию)
- P1: Расширение Telegram-бота для обработки онлайн-заказов
- P2: Экспорт отчётов, система лояльности, мультиязычность
