# PRD: Личный кабинет ресторана

## Дата создания: 2026-01-26
## Последнее обновление: 2026-02-13 (часть 3)

### Изменения 2026-02-13 (часть 3)
- **Якорные ссылки на категории клиентского меню (P1, DONE)**:
  - **Цель**: возможность делиться прямой ссылкой на конкретную категорию (например, `https://menu-mine.by/1#vina` откроет меню сразу на «Вина»).
  - **Frontend `lib/slugify.js`** — новый helper: RU→EN транслитерация + kebab-case (напр. «Бургеры и Сэндвичи» → `burgery-i-sendvichi`). Используется как для генерации URL, так и для матчинга при заходе по ссылке.
  - **`ClientMenuPage.jsx`** — 2 новых useEffect:
    - **Deep-link init**: при первой загрузке `data.categories` читает `?cat=` / `?category=` из query или `#slug` из hash, находит категорию по `id` или по slugified name, переключает секцию (если нужно), скроллит через `setTimeout(200ms)` (даём React отрендерить новую секцию — refs становятся доступны).
    - **URL-sync**: при переключении активной категории (через клик на таб или скролл-spy) обновляет `window.location.hash` через `history.replaceState` — юзер может копировать deep-link прямо из адресной строки.
  - **`SortableCategoryItem.jsx`** (админка) — рядом с каждой категорией новая иконка `Link` (data-testid `copy-category-anchor-{id}`): при клике копирует `#slug` в буфер обмена + показывает toast «Скопировано: #zakuski — добавьте к URL меню». Fallback на `document.execCommand('copy')` для не-HTTPS окружений.
  - **Verification** (preview, `/demo/1`):
    - `?cat=<uuid>` → категория «Starters» проскроллена в viewport (bounding y=198.5), таб подсвечен мятным, URL автоматически обновлён до `#zakuski`.
    - `#zakuski` (только hash) → идентичное поведение, hash сохранён.
    - Работает и для категорий из другой секции (Kitchen↔Bar): секция переключается автоматически.

### Изменения 2026-02-13 (часть 2)
- **Импорт меню Lunchpad — поддержка 3-х уровней вложенности (P0, DONE)**:
  - **Bug**: при импорте `.data`-файла Lunchpad терялись все позиции, лежащие на 3-м уровне (Барное меню → Пиво → Разливное → бутылки). Пользовательский тест на файле `menu (5).data`: импортёр заводил 216 позиций, реально в файле 400 type=4 → потеря 184 (46%). Целые подкатегории Пиво, Вина, Виски, Игристые, Шампанское, Водка, Ром, Текила, Джин, Вермут, Ликёры, Коньяк не появлялись в БД.
  - **Root cause**: `parse_lunchpad_data` (`/app/backend/routes/menu.py`) обрабатывал только 2 уровня. Внутри подкатегории строка `if sub_item.get("type") != 4: continue` отбрасывала вложенные `type=0` (3-й уровень), а реальные бутылки лежали именно там.
  - **Fix**: парсер переписан рекурсивно. Введены хелперы `_parse_lunchpad_price`, `_parse_lunchpad_dish`, `_parse_lunchpad_banner`, `_walk_lunchpad_items`. Любая глубина дерева сплющивается в плоский список категорий с конкатенированными именами вида `«Родитель — Дитя — Внук»` (наша БД-модель одноуровневая). «Оболочечные» родительские категории без собственных блюд (например, «Барное меню») больше не создаются, чтобы не загромождать админку.
  - **Verification на реальном файле пользователя**: 61 категория, 400 dishes + 4 баннера = **404 items (100% от type=4 в файле)**.
  - **Регрессионный тест**: `/app/backend/tests/test_lunchpad_nested_import.py` — 5/5 проходят.

- **Массовое переименование категорий (P1, DONE)**:
  - **Контекст**: после фикса импорта Lunchpad появляются длинные имена («Барное меню — Вина \ Wines — Вино красное \ Red wine»), которые громоздко смотрятся в клиентском меню. Нужно дать админу инструмент быстро их сократить.
  - **Backend**: новый endpoint `POST /api/restaurants/{rid}/categories/bulk-rename` принимает `[{id, name}]`, обновляет имена, сбрасывает `name_en`/`name_zh` для повторного перевода. Возвращает `{updated, skipped}`. Перевод запускается **одной фоновой задачей-батчем** `_translate_categories_batch_bg` (последовательно, с `sleep(0.2)` между категориями) — не залпом, чтобы не перегружать LLM API при rename 50+ категорий.
  - **Frontend**: компонент `BulkRenameCategoriesDialog` в `MenuDialogs.jsx`. Кнопка «Переименовать» (data-testid `bulk-rename-categories-btn`) в шапке MenuPage. Диалог содержит:
    - Inputs «Найти» / «Заменить на» + кнопка «Применить» — массовая замена по подстроке во всех именах.
    - Авто-предлагаемые префиксы для быстрого удаления (например «Барное меню — ») — детектируются по разделителю ` — `.
    - Таблица всех категорий: слева старое имя, справа input нового. Изменённые подсвечиваются мятным.
    - Счётчик «Изменено: N из M», кнопка «Сохранить N» (disabled когда 0).
  - **Тесты**: `/app/backend/tests/test_bulk_rename_categories.py` (5 кейсов: happy-path, invalid items skipped, empty list, cross-restaurant isolation, auth) + регрессия `test_lunchpad_nested_import.py` (5). **10/10 проходят**.
  - **Testing agent**: 100% success backend и frontend, баг race-condition в его тесте на `name_en="" сброс` поправлен (между bulk-rename response и GET успевает отработать фоновый перевод).

### Изменения 2026-02-13
- **SSL/Nginx — окончательный фикс рецидивирующего бага (P0, DONE)**:
  - **Контекст**: на VPS совместно работают два проекта (`Menu_rest2` + `wm-finance`), они шарят один nginx-контейнер `menu_rest2-nginx-1`. Третий раз подряд после деплоя wm-finance клиентские домены `catch-menu.by` и `menu-myatasportivnaya.by` начинали отдавать чужой сертификат `rest-menu.by`.
  - **Истинный root cause** (раскопан в этой сессии): `wm-finance/deploy.sh` копирует свой шаблон `deploy/menu_rest2-nginx-combined.conf` поверх боевого `/root/Menu_rest2/nginx/nginx.conf`. В этом шаблоне **отсутствовала директива** `include /etc/nginx/custom-domains/*.conf;` — поэтому Nginx переставал «видеть» конфиги клиентских доменов, и все SNI ловил default-сервер (`rest-menu.by` как первый `listen 443`). Симптом «слетел сертификат» = просто отсутствие server-блока для домена.
  - **Дополнительная проблема**: `deploy.sh` после копирования делал `nginx -s reload` или `docker kill -s HUP` — оба не подхватывают include-файлы корректно. То же касалось certbot deploy-hook.
  - **Fix №1 — certbot (в репо `/app/docker-compose.yml`)**: deploy-hook `'docker kill -s HUP menu_rest2-nginx-1'` → `'docker restart menu_rest2-nginx-1'`. Гарантирует подхват свежевыпущенных сертификатов после auto-renew.
  - **Fix №2 — VPS hot-fix**: вставлена директива `include /etc/nginx/custom-domains/*.conf;` в `/root/Menu_rest2/nginx/nginx.conf` (последней в `http {}`); `docker compose restart nginx`. Все 4 домена немедленно начали отдавать корректные сертификаты.
  - **Fix №3 — VPS wm-finance**: вставлена та же `include` в `/root/wm-finance/deploy/menu_rest2-nginx-combined.conf`; `deploy.sh` поправлен — обе вызовы `nginx -s reload` / `docker kill -s HUP` заменены на `docker restart menu_rest2-nginx-1`.
  - **Финальная верификация**: `certbot renew --dry-run` успешен для всех 4 доменов; `openssl s_client` подтвердил, что каждый домен (rest-menu.by, catch-menu.by, menu-myatasportivnaya.by, wm-finance.pl) отдаёт собственный валидный cert.
  - **Repo commit**: фикс docker-compose.yml в `/app` готов к Save to GitHub. Фиксы в репо `wm-finance` (include в combined-конфиге + restart в deploy.sh) пользователь зафиксирует через чат проекта wm-finance (выдано готовое сообщение для агента).
- **HTML-парсер переносов блюд Caffesta — отклонено пользователем**: API возвращает 500 на все эндпоинты переносов, альтернативный HTML-scraping админки решено не реализовывать. Фича закрыта, из бэклога убрана.

### Изменения 2026-02-05 (часть 4)
- **Debug-эндпоинт сырого тела п/ф + AI-помощь в Песочнице (P1, DONE)**:
  - **Backend `services/caffesta.py::caffesta_subproduct_debug`** — отдельный helper, возвращает до 5 сырых объектов Caffesta (без нормализации) с фильтром по подстроке имени. Endpoint `GET /api/restaurants/{rid}/caffesta/subproduct-debug?name=лук` (только админ).
  - **`caffesta_get_sub_products`** теперь сканирует ВСЕ ключи объекта на любые `cost`/`price`/`sebes`/`self` — не только фиксированный список. Также возвращает `raw_sample_keys` и `raw_sample` (первый объект целиком) для диагностики.
  - **UI**: в диалог «Диагностика п/ф» добавлена секция «Сырое тело конкретного п/ф» — input + кнопка «Показать тело». Раскрывает все поля Caffesta для подходящих п/ф. Так находим, в каком экзотическом поле спрятана себестоимость, когда обычные пусты.
  - **AI → Песочница (передача данных)**: кнопка «Открыть в Песочнице» в AIParseDialog теперь реально передаёт данные dish-блока в форму Песочницы — заполняет название, ингредиенты с unit_cost из каталога, и список «вручную» для непросопоставленных строк. Между диалогом и Песочницей появляется toast «Загружено из AI: N ингредиентов, K вручную».

### Изменения 2026-02-05 (часть 3)
- **«Возможно вы имели в виду…» в AI-парсере (P2, DONE)**:
  - **Backend `services/recipe_parser.py::_get_suggestions`** — для каждой непросопоставленной строки возвращает top-3 кандидатов из каталога с confidence в диапазоне [45%, 75%) через RapidFuzz. Результат добавляется как `ingredient.suggestions = [{name, caffesta_product_id, local_subproduct_id, self_cost, confidence, type}]`.
  - **Frontend AIParseDialog** — под warning'ом «⚠ Не найдено в каталоге» показываем строку «Возможно:» с амбер-чипами; клик по чипу одним действием привязывает кандидат к строке (обновляет `matched`, `confidence`, очищает `suggestions`, обновляет `stats.matched/unmatched`). Никаких доп. диалогов — «один клик — и всё найдено».
  - Регрессия: `test_did_you_mean_suggestions` в `test_recipe_parser.py`. Все 6/6 тестов проходят.

### Изменения 2026-02-05 (часть 2)
- **Локальные п/ф + AI Chef Assistant (P1, DONE)**:
  - **Backend `services/recipe_parser.py`**: чисто-питоновский парсер сообщений повара. Разделяет текст на блоки (по пустой строке), внутри блока: 1-я строка = title, последняя «Выход N» = yield в граммах, средние = `<name> <qty>[<unit>]`. Каждое имя матчится через RapidFuzz (WRatio ≥ 75) на каталог Caffesta + локальные п/ф. Inline-определённые п/ф (первые блоки) автоматически становятся доступными для матчинга в финальном блюде с приоритетом над каталогом.
  - **Endpoint `POST /api/restaurants/{rid}/recipes/ai-parse`** возвращает `{blocks: [{kind: 'subproduct'|'dish', title, yield_g, ingredients[]}], stats: {matched, unmatched, blocks}}`. Устойчив к отсутствию Caffesta (работает только на локальных п/ф).
  - **CRUD локальных п/ф**: коллекция `local_subproducts` (`{id, restaurant_id, name, yield_g, ingredients[], total_cost, cost_per_kg, notes}`), эндпоинты `GET/POST/PUT/DELETE /api/restaurants/{rid}/local-subproducts`. Себестоимость авто-считается: `total_cost / yield_g * 1000 = cost/кг`. При DELETE возвращает `in_use_recipes` если п/ф использовался в блюдах меню (warning).
  - **Cost catalog** дополнен `is_local_subproduct=true` записями (наверху списка). Caffesta-эндпоинт стал устойчив к отсутствию Caffesta API (для preview-окружения).
  - **Frontend**:
    - В шапке Калькуляции — фиолетово-фуксиевая кнопка **«🪄 Распознать из текста»**. Открывает диалог: textarea + пример повара + кнопка «Распознать»; результат показывает блоки с подбором ингредиентов и кнопками «Сохранить как лок. п/ф» / «Открыть в Песочнице».
    - Новая вкладка **«Мои п/ф»** (с бейджем-счётчиком) — карточки локальных п/ф, кнопки `Pencil` (редактировать) / `Trash2` (удалить с подтверждением). Форма создания/редактирования: имя, выход (г), ингредиенты из каталога, авто-расчёт total_cost / cost_per_kg.
    - Бейдж **«лок. п/ф»** (синий) рядом с названием в picker'ах ингредиентов (recipe editor + sandbox + форма локального п/ф).
  - **Тесты** `/app/backend/tests/test_recipe_parser.py` (5 кейсов): 2-блочный paste, единицы по умолчанию = граммы, ё-нормализация, пустой текст, single-block = dish. Все проходят.

### Изменения 2026-02-05
- **Полуфабрикаты Caffesta в калькуляторе себестоимости (P0, DONE)**:
  - **Probe-диагностика выявила** (rest-menu.by на проде): рабочий URL — `/v1.0/draft/get_products/{pos_id}/0/0?type=sub_product` (HTTP 200, 1000 строк). `get_semi_products`, `get_blanks`, `get_compositions`, `semi_products`, `blanks` все возвращают 500.
  - **Backend**: `caffesta_get_sub_products()` теперь использует только проверенный URL с пагинацией (по 1000), парсит `self_cost`/`avgInvoicedSelfCost`/`cost`/`self_price`/`cost_price` (берёт первое непустое).
  - **Защита от ложных срабатываний**: в `get_cost_catalog` есть guard — если множество ID полуфабрикатов покрывает >80% обычных продуктов (т.е. фильтр Caffesta игнорируется), sub-products отбрасываются с warning'ом в логах.
  - **Endpoint** `GET /api/restaurants/{rid}/cost-catalog` отдаёт полуфабрикаты с флагами `is_sub_product=true`, `type='sub_product'`, всегда видны (без зависимости от toggle тех.карт).
  - **UI**: в picker'е ингредиентов калькулятора рядом с названием появляется бейдж «п/ф» (амбер) для полуфабрикатов; подпись «Полуфабрикат» вместо «Сырьё». Применено в обоих picker-ах (recipe editor + sandbox).
  - **Diagnostic UI**: кнопка «🔍 Диагностика п/ф» в шапке калькулятора → модалка с результатом probe (HTTP/JSON/rows), для каждой строки можно раскрыть body sample.

### Изменения 2026-05-04
- **Share-card для соцсетей (P1, DONE)**:
  - **Backend**: `services/share_card.py::render_share_card()` — generalized PNG-генератор. Поддерживает 2 формата: `square` (1080×1080 — IG-посты, Telegram, WhatsApp) и `story` (1080×1920 — IG Stories/Reels). Подтягивает logo ресторана (если задан в `restaurant.logo_url`) и рендерит округлый logo-чип в шапке. Слоган берётся из `restaurant.slogan`. URL в QR — из X-Forwarded headers.
  - **Admin endpoint** `GET /api/restaurants/{rid}/tables/{tid}/share-card?fmt=square|story&base_url=...` (auth required, проверка `check_restaurant_access`). Отдаёт PNG как attachment.
  - **Frontend**: в `SettingsPage.jsx` → диалог QR-кода стола → новые кнопки «Соцсети 1:1» и «Stories 9:16» под разделителем с подписью «Готовая карточка для соцсетей (с логотипом, QR и брендом)». Скачивание через axios + blob URL.
  - **Public endpoint** `GET /api/public/demo-share-card` остался — отдаёт квадратную карточку для публичного `/demo` лендинга.
  - Проверено: square=68KB, story=107KB, кириллица рендерится без артефактов (Liberation Sans), QR корректно декодируется на production-URL.
  - Регрессия: 12/12 тестов demo isolation + translation cache проходят.

- **Изолированный демо-ресторан + кэш AI-переводов (P1, DONE)**:
  - **Demo Restaurant (slug=`demo`)** — отдельный посевной ресторан c полным набором моковых данных, создаётся через `services/demo_seed.py::seed_demo_restaurant()` и привязывается к юзеру `demo/demo2026`. Раньше demo юзер видел реальный ресторан «Мята Спортивная»; теперь имеет доступ только к Demo Restaurant.
  - Содержимое: 2 секции (Кухня/Бар), 11 категорий, 25 блюд (с RU и EN переводами + Unsplash фото), 8 столов, 45 заказов за 7 дней, 20 вызовов персонала, 180 просмотров меню, 3 типа вызовов. Все таймстемпы рандомизированы для красивых графиков в Analytics.
  - `/api/seed` идемпотентен: повторный вызов не дублирует данные. Outer-guard на `orders >= 30` гарантирует, что менюviews/calls не растут.
  - `helpers.create_demo_user(demo_restaurant_id)` принимает rid явно; если `restaurant_ids` юзера расходится — обновляет.
  - **Translation cache** — новая коллекция `translation_cache` (unique index на `key_ru`). Pre-seed на 63 общих менюшных слова (Капучино, Карбонара, Цезарь, …). На каждый перевод сначала смотрим в кэш, потом дёргаем LLM и upsert'им результат. Замер: cache hit < 1ms, LLM call ~3-5 сек. Новый endpoint `GET /api/translation-cache-stats` для диагностики.
  - Smoke-тесты `/translation-status` и `translate-all` теперь принудительно вызывают LLM (`use_cache=False`) — кэш не маскирует проблемы с ключом.
  - Регрессия: `/app/backend/tests/test_demo_isolation_and_translation_cache.py` — 12 кейсов, все проходят.

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
- **Мультиязычность клиентского меню RU↔EN (P2, DONE)**:
  - **Backend**: новый сервис `services/translation.py` (Gemini 2.5 Flash через `emergentintegrations`, система-промпт = «menu translator»). Добавлены поля `name_en`/`description_en` в модели `MenuItem`, `MenuSection`, `Category`, `CallType`. Endpoint'ы создания/обновления menu-items/categories/sections ставят фоновую задачу перевода через `BackgroundTasks` — пользователь админки получает ответ мгновенно, EN-поля заполняются через секунду.
  - Bulk endpoint `POST /api/restaurants/{rid}/translate-all[?force=true]` — фоновая задача, которая дотранслирует все существующие блюда/категории ресторана (возвращает estimate сразу, перевод идёт в фоне, `asyncio.sleep(0.1)` между блюдами чтобы не блокировать event loop).
  - EN-перевод автоматически сбрасывается при редактировании RU-текста (next hit бэкенда перегенерит).
  - **Frontend**: новый `lib/i18n.js` (Map RU/EN, auto-detect `navigator.language`, persist в `localStorage`), компонент `LanguageSwitcher.jsx` (пилл-переключатель RU/EN с флагами в хедере клиентского меню). `ClientMenuPage` использует `t(key)` для UI-строк и `getLocalized(doc, 'name'|'description', lang)` для контента (fallback на RU если `*_en` пустое).
  - Проверено: на демо-ресторане `Мята Спортивная` переведено 135+/213 блюд и 50/50 категорий. EN-меню показывает «Breakfasts until 4 PM», «Syrniki with sour cream and Rosemary Cherry sauce», «Call waiter» и т.д. Админка намеренно оставлена на русском (для сотрудников).

- **DemoPage переориентирована на владельцев ресторанов (P1, DONE)**:
  - Полный рерайт страницы: убраны технические разделы («Архитектура», «Технические находки», SVG-диаграммы стека), оставлены маркетинговые блоки.
  - **Hero**: заменён на autoplay-видео `/demo.mp4` (записан Playwright-screencast'ом, 22 сек, 1 МБ). Poster — OG-картинка для fallback. Floating-чипы «Новый заказ» / «+12% к выручке».
  - **Benefits**: 6 цветных карточек с конкретными выгодами для владельца («Гости заказывают сами», «Уведомления в Telegram», «Понятная аналитика», «Доставка и предзаказ», «Меню для туристов», «Свой домен и бренд»).
  - **Screenshots**: реальные скриншоты живого сервиса в `/app/frontend/public/demo-shots/` (admin orders / analytics / menu management — desktop, client menu EN — mobile в phone-frame'ах). Каждый скриншот в «browser chrome» обрамлении.
  - Live-метрики и блок «Попробуйте меню как гость» с QR-кодом сохранены, перенесены в логичные секции.
  - Финальный CTA: данные для входа `demo/demo2026` + Telegram `@king_saas` для подключения своего ресторана.

- **Production-ready доводки (P1, DONE)**:
  - **OG-теги в `frontend/public/index.html`** — статичные мета-теги (`og:title/description/image`, `twitter:card`) попадают в исходный HTML, поэтому Telegram, WhatsApp, Facebook и Discord корректно показывают превью при шере ссылки. Динамический `useEffect` на DemoPage перезаписывает их для пользователей-людей.
  - **Кнопка «Перевести всё меню на английский»** добавлена в Settings → новая вкладка «Переводы» (`tab-i18n`). Вызывает `POST /api/restaurants/{rid}/translate-all`, опция `force=true` доступна чекбоксом, после запуска показывает estimate (количество разделов/категорий/блюд).
  - **Скрипт `scripts/record_demo_video.py`** — Playwright-screencast 1280×720, проходит по клиентскому меню (RU+EN), админке (заказы, аналитика). Конвертация WebM → MP4 через ffmpeg. Output: `frontend/public/demo.{webm,mp4}`.
  - **Видео-субтитры** в hero — 5 синхронизированных подсказок («Гость сканирует QR» → «Листает категории» → «Один клик — английский» → «Ресторан видит заказы» → «Аналитика за период»). Сегментный progress-bar сверху видео показывает прогресс по «главам». Текст обновляется через `timeupdate` event.
  - **Селлинговые метрики** заменили live-stats: «+24% к среднему чеку», «−40% времени официантов», «<1 день запуск», «99.9% аптайм», «0 ₽ за приложения». Endpoint `/api/public/demo-stats` остался для будущего использования, на DemoPage больше не вызывается.
  - **Секция AI-мультиязычности** на DemoPage — отдельный блок «Меню для иностранных гостей — без ручной работы» с парами bilingual-карточек RU↔EN (показывают пример как «Сырники со сметаной» становится «Syrniki with sour cream»), 4 преимущества и amber-подсказкой про разовый запуск из админки.

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
