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

## Что умеет

| Тул | Что делает |
|---|---|
| `whoami` | Кто залогинен, какой ресторан активен |
| `list_restaurants` | Все рестораны, к которым есть доступ |
| `select_restaurant(id_or_name)` | Переключиться на ресторан |
| `list_sections` | Секции (Еда / Напитки / Кальянная …) |
| `list_categories` | Категории меню |
| `list_menu_items(category_id?, search?)` | Список блюд с фильтром |
| `get_menu_item(id)` | Детали одного блюда |
| `create_menu_item(name, price, category_id, ...)` | Создать блюдо |
| `update_menu_item(id, updates)` | Обновить любые поля |
| `delete_menu_item(id)` | Удалить блюдо |
| `create_category(name, section_id?)` | Создать категорию |
| `update_category(id, updates)` | Изменить категорию |
| `bulk_rename_categories({id: new_name})` | Массовое переименование |
| `bulk_update_prices([{id, price}])` | Массовое обновление цен |
| `bulk_update_items([{id, ...fields}])` | Любые массовые правки |
| `list_caffesta_products(search?)` | Каталог POS Caffesta |

---

## Полезные промпты

**Обновить цены из фото прайса:**
> Вот фото нашего нового прайса на коктейли *(прикрепить)*. Обнови цены в базе — старые названия могут отличаться, ищи через `list_menu_items(search=...)` по ключевым словам.

**AI-переписать описания:**
> Пройди по всем блюдам категории «Салаты» и сделай описания короче и аппетитнее — не более 100 символов. Используй `bulk_update_items` в конце.

**Пометить популярное как хит:**
> Проставь `is_hit: true` для всех блюд из категории «Завтраки», у которых в названии есть «Гранола», «Овсянка» или «Сырники».

**Скрыть 0-цену:**
> Найди все блюда с ценой 0 и сделай их `is_available: false`.

---

## Безопасность

* JWT-токен хранится только в памяти процесса; при рестарте Claude Desktop он получит новый через login.
* MCP-сервер работает **локально** на твоей машине и общается с REST-MENU по HTTPS. Никакие данные не уходят в сторонние сервисы.
* Если хочешь ограничить Claude в правах — создай отдельного пользователя в REST-MENU с ролью «менеджер» (у него нет доступа к финансовым отчётам).
