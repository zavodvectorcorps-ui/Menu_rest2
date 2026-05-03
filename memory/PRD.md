# PRD: Личный кабинет ресторана

## Дата создания: 2026-01-26
## Последнее обновление: 2026-05-03

### Изменения 2026-05-03
- **DemoPage — публичный SaaS-лендинг (P1, DONE)**:
  - Новая публичная страница `/demo` без авторизации (`/app/frontend/src/pages/DemoPage.jsx`).
  - Dark-тема (#0a0e1a), hero с параллаксом + градиентные orbs, моковый dashboard (faux browser chrome), 9 feature-карточек, секция архитектуры с SVG-блоками, tech-стек (12 технологий), 5 технических «находок», финальный CTA.
  - SEO meta-теги: title, description, keywords, og:title, og:description, og:image, twitter:card, canonical link — устанавливаются через useEffect при монтировании, очищаются при unmount.
  - Tailwind config: добавлены оттенки `mint-200/300/400` для поддержки градиентов.
  - Роут зарегистрирован в `App.js` перед `/:tableNumber` (статический приоритет).
- **Демо-доступ + Telegram-контакт на DemoPage (P1, DONE)**:
  - Новый seed-хелпер `create_demo_user()` в `backend/helpers.py` создаёт пользователя `demo/demo2026` с ролью `administrator`, привязанного к двум посевным ресторанам. Вызывается из `/api/seed` после создания ресторанов.
  - При пере-сиде список ресторанов на `demo` обновляется — данные остаются актуальными.
  - DemoPage: финальный CTA переработан в двухколоночный блок — слева данные для входа (login/password с кнопками copy-to-clipboard), справа Telegram-контакт с `@king_saas` (брендовый цвет #229ED9, SVG-логотип Telegram, open in new tab).
- **Блок «Попробуйте меню как гость» на DemoPage (P1, DONE)**:
  - Новый публичный endpoint `GET /api/public/demo-menu-info` возвращает путь к клиентскому меню (`/slug/N` или `/menu/{code}`) первого активного стола (№≥1) первого демо-ресторана.
  - На DemoPage добавлена секция с phone-mockup (notch, рамка), внутри QR-код (`qrcode.react`) с ссылкой на живое клиентское меню. Справа — 4 преимущества и кнопка «Открыть меню в новой вкладке».
  - QR-код генерится на клиенте (SVG) — не зависит от внешних API, работает offline после загрузки страницы.
- **Live-метрики на DemoPage (P1, DONE)**:
  - Новый публичный endpoint `GET /api/public/demo-stats` агрегирует 6 метрик по демо-ресторанам: количество ресторанов, активных столов, позиций в меню, просмотров меню (total + 24h delta), заказов (total + 24h), вызовов официанта.
  - Статичный блок «Metrics» на DemoPage заменён на динамический с «live» пульсирующей точкой, иконками Lucide и count-up анимацией (requestAnimationFrame, ease-out cubic 900ms).
  - Дельта «+N / 24ч» бейджем для метрик с реальным трафиком (заказы, просмотры).
- **OG-image для шер-карточек (P1, DONE)**:
  - Сгенерирована через Gemini Nano Banana (`gemini-3.1-flash-image-preview`) — dark hero 1200×630, бренд REST-MENU + phone-mockup + QR-код. Финальный size: 100 KB JPEG, crop до точного aspect 1200×630.
  - Сохранена в `/app/frontend/public/og-image.jpg`. Meta-теги на DemoPage обновлены: `og:image`, `og:image:width=1200`, `og:image:height=630`, `og:image:type=image/jpeg`, `twitter:image`.
  - `EMERGENT_LLM_KEY` добавлен в `backend/.env`.
- **Динамическая валюта в админ-дашбордах (P1, DONE)**:
  - Убран хардкод `BYN` из `CaffestaPage.jsx`, `FactualMarginPage.jsx`, `AnalyticsPage.jsx`, `OrdersPage.jsx`, `CaffestaMappingPage.jsx`, `AdminLayout.jsx` (toasts). Теперь валюта берётся из `restaurant.currency` через `useApp()` (fallback `'BYN'`).
  - Шаблон: `const cur = restaurant?.currency || 'BYN';` + замены ``` ${revenue} BYN` ``` → ``` ${revenue} ${cur}` ``` и `{x} BYN` → `{x} {cur}` (JSX text). Особый случай — JSX-атрибут string → template literal: `title="Выручка ({cur})"` → `` title={`Выручка (${cur})`} ``.
  - CSV-экспорт в FactualMargin теперь тоже использует актуальную валюту в заголовке столбца.

### Изменения 2026-05-02 (часть 4)
- **Полуавтоматическая привязка кастомных доменов (P1, DONE)**:
  - Backend: новый диагностический endpoint `GET /api/restaurants/{rid}/domains/check?domain=X` (только суперадмин). Делает 3 проверки: DNS-резолв (`getaddrinfo`), HTTPS-доступность (`/api/health`), привязка к этому ресторану. Возвращает `{overall: ok|warning|error, dns, https, binding, summary}`.
  - Frontend: в `RestaurantModulesPage` рядом с каждым доменом — кнопка «Проверить», ссылка «открыть», статус-иконка (зелёный CheckCircle / жёлтый AlertTriangle / красный AlertCircle) с человечным summary. При verdict ≠ 'ok' показывается готовая команда `./scripts/add-domain.sh DOMAIN` с кнопкой «Скопировать».
  - Развёрнутая 6-шаговая инструкция (раскрывающийся details-блок): купить домен → A-запись на IP VPS → добавить в админке → запустить скрипт по SSH → проверить → QR работает.
  - Скрипт `/app/scripts/add-domain.sh` переписан: проверяет DNS перед certbot (читает публичный IP сервера, сравнивает с A-записью домена), идемпотентный (пропускает уже добавленный блок и существующий сертификат), печатает понятные ошибки и пост-инструкцию.

### Изменения 2026-05-02 (часть 3)
- **Bulk QR PDF (P2, DONE)**: Endpoint `GET /api/restaurants/{rid}/tables/qr-pdf-all?size=a5|a6` возвращает один PDF со всеми активными столами ресторана (одна страница на стол). Используется общий хелпер `_qr_draw_page()` (рефакторинг single-PDF endpoint'а). Логотип скачивается один раз и переиспользуется. Кнопки «Все QR (A5)» и «Все QR (A6)» в шапке вкладки «Столы» в настройках. Идеально для отдачи в типографию одним файлом.

### Изменения 2026-05-02 (часть 2)
- **Модуль "Корзина" (cart_only) (P1, DONE)**: Новый feature-flag `cart_only` в `enabled_modules`. Когда включён — гость собирает блюда в корзину, видит окно «Покажите заказ официанту» с номером стола, кнопками «Очистить» и «Готово». На кухню/в Telegram ничего не отправляется. Кнопки «+» в меню видны даже если `online_orders_enabled=false`. Реализовано в `ClientMenuPage.jsx` + переключатель в `RestaurantModulesPage.jsx`.
- **Кастомные домены (P1, DONE)**: Поле `custom_domains: List[str]` в модели Restaurant. Суперадмин в `/admin/restaurant-modules` управляет списком доменов на каждом ресторане (нормализация к lowercase, без http/портов, проверка уникальности). Новый публичный endpoint `GET /api/public/menu-by-domain/{table_number}` определяет ресторан по Host-заголовку (или `?host=`). Frontend route `/:tableNumber` в режиме `domainMode` вызывает этот endpoint. Скрипт `/app/scripts/add-domain.sh DOMAIN` добавляет server-блок в Nginx + получает Let's Encrypt SSL.
- **PDF-шаблон QR-кода для печати (P1, DONE)**: Endpoint `GET /api/restaurants/{rid}/tables/{tid}/qr-pdf?size=a5|a6` использует `reportlab` + `qrcode`. PDF содержит: рамку, логотип ресторана (если есть), название, заголовок "Отсканируйте код, чтобы открыть меню", QR-код, "Стол №N", URL внизу. Шрифт DejaVu для кириллицы (добавлен `fonts-dejavu-core` в Dockerfile). Кнопки «PDF A5» и «PDF A6» в QR-диалоге `SettingsPage`.

### Изменения 2026-05-02
- **Telegram webhook auto-detect (P0, DONE)**: webhook URL теперь вычисляется автоматически из заголовков входящего запроса админа (`X-Forwarded-Host` + `X-Forwarded-Proto`). Помощник `_resolve_public_base_url()` в `routes/telegram.py`. `PUBLIC_BASE_URL` env-переменная остаётся опциональным override. Фикс ошибки "Не задан PUBLIC_BASE_URL" при подключении бота на новых ресторанах (Мясная лавка).
- **Защита Nginx от 502 Bad Gateway (P0, DONE)**: `nginx/nginx.conf` использует встроенный DNS Docker (`resolver 127.0.0.11 valid=10s`) и динамический upstream через переменные (`set $backend_upstream "backend:8001"; proxy_pass http://$backend_upstream;`). При пересборке backend-контейнера Nginx автоматически перерезолвит новый IP без рестарта. Добавлен `proxy_next_upstream` для отказоустойчивости и `X-Forwarded-Host` для авторезолва webhook-домена.

### Изменения 2026-04-27 (часть 2)
- **Fuzzy-маппинг блюд с Caffesta (P1, DONE)**:
  - `rapidfuzz` (token_sort_ratio) + нормализация (lowercase, удаление пунктуации)
  - `GET /caffesta/auto-mapping/suggest?threshold=60&only_unmapped=true` — топ-3 кандидата на каждое блюдо
  - `POST /caffesta/auto-mapping/apply` — batch-применение маппингов
  - Страница `/admin/caffesta-mapping` с слайдером порога (40–95%), поиском, чекбоксом «только непривязанные», карточками кандидатов (подсветка: ≥85% — зелёный, ≥70% — жёлтый), кнопкой «Применить (N)»
  - Авто-преселект кандидатов со score ≥ 85%
- **Ежедневный Telegram-дайджест (enhancement, DONE)**:
  - `APScheduler` с cron `10:00 Europe/Minsk` + `run_daily_digest_job()` в `startup`
  - Настройки в `Settings`: `daily_digest_enabled`, `daily_digest_bot_token`, `daily_digest_chat_id`, `daily_digest_windows: [{name, time_from, time_to}]` (до 4 окон)
  - Дефолтные окна: Завтрак 08–12, Обед 12–16, Вечер 18–23
  - `GET /digest/preview` — предпросмотр текста, `POST /digest/send` — ручная отправка
  - Содержит: вчерашняя выручка + чеки + средний чек, сравнение ▲▼ % с тем же днём недели прошлой недели, разбивка по окнам, топ-3 позиций, разбивка по способам оплаты
  - Fallback на общий `telegram_bot_token`/`telegram_chat_id`, если не задан отдельный токен/chat_id для дайджеста
  - Вкладка «Дайджест 10:00» в Caffesta-странице с тумблером, настройкой окон, предпросмотром и кнопкой «Отправить сейчас»

### Изменения 2026-04-27
- **Контроль цен и маржинальности (P0)** — полностью запущен:
  - Страница `/admin/price-control` (доступна по ссылке «Контроль цен» в сайдбаре).
  - Загрузка себестоимости CSV/XLSX, сопоставление блюд по нормализованному имени или `caffesta_product_id`.
  - Импорт себестоимости из Caffesta API: переписан на `/a/v1.0/draft/get_balances/{pos_id}/0` (было неправильно `/api/v1/products`). Матчинг по `caffesta_product_id`.
  - Расчёт маржи по каскаду порогов: позиция → категория → общий (по умолчанию 30%). Статусы `ok/warning/critical`.
  - Telegram-алерты при падении маржи ниже `(порог − 5)%`.
- **Caffesta — виды оплаты (несколько)**: список `payment_methods: [{name, payment_id, is_default}]` с звёздочкой для дефолтного. Старое поле `payment_id` сохранено.
- **Caffesta — «Сравнение по времени» (v2)**: endpoint `/caffesta/time-window` полностью переписан на `/a/v1.1/draft/receipts_by_shift_day/{terminal_id}/{date}` — получает РЕАЛЬНЫЕ timestamp'ы (`created_at`). Параллельная загрузка по всем терминалам (авто-discovery через `export_sales_totals?add_gr_by=terminal_id`) и дням периода. Лимит: 120 дней.
- **Caffesta — оплата по типам (v2)**: агрегация теперь по `cash_pay`/`card_pay`/`cashless_pay` + `cashlessPayment_id` → маппинг в пользовательский `payment_methods`. Показывает все виды оплат, а не только Наличные/Карта.
- **Caffesta — синхронизация стоп-листа (P1, DONE)**: endpoint `POST /caffesta/stop-list/sync` использует `/a/v1.0/draft/get_product_shop_data/{pos_id}/0` → поле `inStopList`. Автоматически скрывает в меню позиции, которые в Caffesta на стоп-листе (`is_available=false`, `stop_list_source="caffesta"`); повторная синхронизация возвращает их обратно. Позиции, отключённые вручную, не трогаются. Кнопка на вкладке Настройки Caffesta.


### Изменения 2026-04-21
- Клиентское меню (`ClientMenuPage.jsx`): непрерывный скролл всех блюд текущей секции единым списком с группировкой по категориям. Sticky-шапка с категориями всегда видна. Клик по категории — плавный скролл-якорь с учётом высоты шапки. IntersectionObserver (ScrollSpy) автоподсвечивает активную категорию и автоматически центрирует её в горизонтальном слайдере при скролле.
- Добавлен **поиск по меню**: inline-строка поиска в sticky-шапке фильтрует блюда в текущей секции по названию и описанию. Пустые категории скрываются из навигации. Пустое состояние с кнопкой «Сбросить поиск».

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

### Кастомные URL (slug) для клиентского меню (2026-03-11)
- Поле `slug` в модели ресторана с валидацией (уникальность, формат: a-z, 0-9, -)
- Новый публичный эндпоинт: `GET /api/public/menu-by-slug/{slug}/{table_number}`
- QR-коды генерируются со slug-URL если у ресторана задан slug
- Фронтенд маршрут `/:slug/:tableNumber` → ClientMenuPage
- Старый формат `/menu/:tableCode` продолжает работать
- Поле ввода slug в настройках ресторана с превью URL
- Ссылки на столы и кнопка "Открыть меню" используют slug-формат
- Улучшена мобильная навигация по категориям: стрелки + градиентные индикаторы скролла

### Интеграция с Caffesta POS (2026-03-12)
- Backend-сервис `services/caffesta.py`: клиент API (тест подключения, отправка заказов, аналитика, товары)
- Роуты `routes/caffesta.py`: CRUD настроек, тест подключения, аналитика POS, отправка заказов
- Автоматическая отправка заказов на кассу Caffesta при их создании (если включено)
- Фронтенд-страница `CaffestaPage.jsx`: настройки подключения + аналитика POS
- Пункт навигации «Caffesta POS» в AdminLayout
- Статус: готово к использованию, ожидает реальные ключи API от пользователя

### Мультитенантность и авторизация
- JWT, роли суперадмин/менеджер

### Telegram-бот, импорт меню (.data/.json), ярлыки, предзаказы

### Telegram-бот: полное управление заказами (2026-03-10)
- Inline-кнопки: "Принять", "Готово", "Отклонить" для заказов; "Принял" для вызовов
- Нажатие кнопки меняет статус в БД, обновляет сообщение, broadcast WS
- /orders — список активных заказов с кнопками
- /calls — список активных вызовов с кнопкой "Принял"
- /stats — статистика (заказы, выручка, вызовы, просмотры)

### Трекер статуса заказа для клиента (2026-03-10)
- Stepper на ClientMenuPage: Принят → Готовится → Готов
- Polling GET /api/public/orders/{id}/status каждые 5 сек
- localStorage для сохранения при обновлении страницы
- Автоочистка через 10 сек после завершения

### Массовое завершение заказов/вызовов

### WebSocket уведомления в реальном времени (2026-03-10)
- WS endpoint: /api/ws/{restaurant_id}?token={jwt}
- Broadcast new_order и new_staff_call при создании через публичный API
- Глобальные toast-уведомления на всех страницах админки
- Звуковое уведомление (AudioContext, включение/выключение в localStorage)
- Индикатор подключения в сайдбаре (зелёная/красная точка)
- Auto-refresh списка заказов на OrdersPage
- Auto-reconnect через 3 сек, ping каждые 30 сек

### Счётчик непрочитанных уведомлений (2026-03-10)
- Красный бейдж на "Заказы" в сайдбаре с количеством новых заказов/вызовов
- Инкремент при каждом WS-событии (new_order, new_staff_call)
- Автосброс при переходе на страницу заказов
- Пульсирующая анимация для привлечения внимания

### Рефакторинг (2026-03-10)
- server.py: 1936 → 62 строки (16 модулей)
- MenuPage.jsx: 1402 → 477 строк (4 компонента)

## Учётные данные
- Суперадмин: admin / 220066
- Рестораны: Мята Спортивная (aa25189d), Catch (d433dc80)

## Бэклог
- P1: Интеграция с Caffesta POS (ожидает API-документацию)
- P2: Экспорт отчётов, система лояльности, мультиязычность
