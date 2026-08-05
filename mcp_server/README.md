# REST-MENU MCP Server

MCP-сервер для управления REST-MENU через Claude Desktop / Cursor / Cline.

Claude получает набор инструментов: `list_menu_items`, `create_menu_item`,
`update_menu_item`, `bulk_update_prices`, `list_caffesta_products` и т.д.,
и работает с меню через обычный REST API.

---

## Установка (Mac / Linux / Windows)

Нужен **Python 3.10+**. Проще всего запускать через [uv](https://docs.astral.sh/uv/) — Claude Desktop сам поднимет процесс.

### 1. Установи uv (если нет)

```bash
# Mac / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex
```

### 2. Склонируй репозиторий и подтяни зависимости

```bash
git clone https://github.com/<your-user>/Menu_rest2.git
cd Menu_rest2/mcp_server

# uv автоматически создаст venv и поставит fastmcp, httpx, python-dotenv
uv sync
```

Проверить, что сервер стартует локально (без Claude — вручную):

```bash
REST_MENU_USERNAME=admin \
REST_MENU_PASSWORD=220066 \
REST_MENU_API_URL=https://rest-menu.by \
uv run restmenu-mcp
# Процесс повиснет и будет ждать stdin от MCP-клиента — так и должно быть.
# Прерви CTRL+C.
```

### 3. Подключи к Claude Desktop

Открой (создай если нет) файл конфига Claude Desktop:

- **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Добавь секцию `mcpServers`:

```json
{
  "mcpServers": {
    "restmenu": {
      "command": "uv",
      "args": [
        "--directory",
        "/абсолютный/путь/к/Menu_rest2/mcp_server",
        "run",
        "restmenu-mcp"
      ],
      "env": {
        "REST_MENU_API_URL": "https://rest-menu.by",
        "REST_MENU_USERNAME": "admin",
        "REST_MENU_PASSWORD": "220066",
        "REST_MENU_DEFAULT_RESTAURANT": "aa25189d-d668-4838-915a-c5d936547f3f"
      }
    }
  }
}
```

`REST_MENU_DEFAULT_RESTAURANT` — необязательно. Если не задать, Claude сам вызовет `list_restaurants` и `select_restaurant`.

Полностью перезапусти Claude Desktop (Cmd+Q / из трея).

### 4. Проверка

Открой Claude Desktop → снизу инпут-поля должна появиться иконка «🔌» с надписью `restmenu`. Задай ему:

> Покажи первые 10 блюд из категории «Завтраки»

Claude сам:
1. Вызовет `list_categories` → найдёт «Завтраки»
2. Вызовет `list_menu_items(category_id=...)` → вернёт список
3. Сформатирует ответ.

---

## Что умеет (45 инструментов)

### Авторизация и рестораны
| Тул | Что делает |
|---|---|
| `whoami` | Кто залогинен, какой ресторан активен |
| `list_restaurants` | Все рестораны, к которым есть доступ |
| `select_restaurant(id_or_name)` | Переключиться на ресторан |

### Меню
| Тул | Что делает |
|---|---|
| `list_sections` | Секции (Еда / Напитки / Кальянная …) |
| `list_categories(section_id?)` | Категории меню |
| `list_menu_items(category_id?, search?)` | Список блюд с фильтром |
| `get_menu_item(id)` | Детали одного блюда |
| `create_menu_item(name, price, category_id, ...)` | Создать блюдо |
| `update_menu_item(id, updates)` | Обновить любые поля блюда |
| `delete_menu_item(id)` | Удалить блюдо |
| `create_category(name, section_id?)` | Создать категорию |
| `update_category(id, updates)` | Изменить категорию |
| `bulk_rename_categories({id: new_name})` | Массово переименовать |
| `bulk_update_prices([{id, price}])` | Массово обновить цены |
| `bulk_update_items([{id, ...fields}])` | Любые массовые правки |

### Заказы и вызовы
| Тул | Что делает |
|---|---|
| `list_orders(status?)` | Все / активные заказы |
| `update_order_status(id, status)` | Сменить статус заказа |
| `complete_all_orders` | Завершить все активные |
| `list_staff_calls(status?)` | Вызовы официанта |
| `update_staff_call_status(id, status)` | Обработать вызов |
| `complete_all_staff_calls` | Обработать все вызовы |

### Аналитика и Telegram-дайджест
| Тул | Что делает |
|---|---|
| `get_analytics(days)` | Заказы через QR-меню за N дней |
| `caffesta_sales_report(from, to)` | Продажи из POS по датам |
| `caffesta_analytics(days)` | Топ-блюда, топ-категории, dynamics |
| `factual_margin(days)` | Фактическая маржа (выручка − себестоимость) |
| `get_digest_preview(date?)` | Превью Telegram-сводки |
| `send_digest_now(date?)` | Отправить сводку сейчас |

### Видео из фото (fal.ai / Kling)
| Тул | Что делает |
|---|---|
| `generate_video_from_image(image_url, prompt, duration)` | Запустить генерацию |
| `check_video_status(request_id)` | Проверить готовность |

### Столы и QR
| Тул | Что делает |
|---|---|
| `list_tables` | Список столов ресторана |
| `create_table(number, name?)` | Добавить стол |

### Splash-заставки и лейблы
| Тул | Что делает |
|---|---|
| `list_splash_ads` / `create_splash_ad` / `delete_splash_ad` | Рекламные попапы |
| `list_labels` / `create_label(name, icon?, color?)` | Кастомные бейджи (Веган, Острое) |

### Настройки ресторана
| Тул | Что делает |
|---|---|
| `get_settings` | Валюта, языки, темы, флаги фичей |
| `update_settings(updates)` | Обновить любые настройки |
| `update_restaurant(updates)` | Ресторан (имя, лого, слоган, телефон) |

### Рецепты и себестоимость
| Тул | Что делает |
|---|---|
| `get_recipe(item_id)` | Тех.карта блюда |
| `set_recipe(item_id, ingredients, yield_g?)` | Установить рецепт |
| `ai_parse_recipe(item_id, raw_text)` | AI-парсинг свободного текста в рецепт |
| `list_caffesta_products(search?)` | Каталог POS Caffesta |

### Переводы
| Тул | Что делает |
|---|---|
| `translate_all_now` | Запустить AI-перевод меню |
| `get_translate_status` | Прогресс перевода |

---

## Полезные промпты

**Работа с ценами и позициями:**
- «Обнови цены из фото прайса *(картинка)* — старые названия могут отличаться, ищи через `list_menu_items(search=...)`».
- «Найди все блюда с ценой 0 и сделай `is_available: false`».
- «Проставь `is_hit: true` всем блюдам категории Завтраки, где в названии есть 'Гранола', 'Овсянка' или 'Сырники'».

**Копирайтинг:**
- «Пройди по всем блюдам категории Салаты, сделай описания короче и аппетитнее (до 100 символов), примени bulk_update_items».
- «Придумай 3 splash-заставки для акции: обед со скидкой 20% с 13:00 до 17:00, создай их через `create_splash_ad`».

**Аналитика:**
- «Покажи топ-10 самых продаваемых блюд за последние 30 дней из Caffesta, сравни с их маржой».
- «Какие блюда с высокой себестоимостью, но низкими продажами? Может стоит убрать?»
- «Отправь превью Telegram-сводки за вчера, я хочу проверить перед отправкой».

**Операционка:**
- «Есть новые вызовы официанта? Отметь все как обработанные».
- «Заверши все висящие заказы».
- «Сколько столов в ресторане и какие ещё не сгенерированы QR?»

**Рецепты и Caffesta:**
- «Вот раскладка на новое блюдо *(вставить текст)* — привяжи ингредиенты к каталогу Caffesta через `ai_parse_recipe` для блюда id=...».
- «Импортируй БЖУ из этого файла и сопоставь с блюдами».

**Мультимедиа:**
- «Оживи фото блюда id=X — сгенерируй короткое видео и подставь в карточку. Промт: cinematic slow zoom on the plate».

**Переводы:**
- «Запусти перевод всего меню на английский и китайский, потом покажи статус».

---

## Безопасность

* JWT-токен хранится только в памяти процесса; при рестарте Claude Desktop он получит новый через login.
* MCP-сервер работает **локально** на твоей машине и общается с REST-MENU по HTTPS. Никакие данные не уходят в сторонние сервисы.
* Если хочешь ограничить Claude в правах — создай отдельного пользователя в REST-MENU с ролью «менеджер» (у него нет доступа к финансовым отчётам).
