#!/usr/bin/env python3
"""
Standalone-диагностика расхождения выручки между Caffesta UI и нашим digest.

Что делает (без зависимостей от нашего бэкенда):
  1. Подключается к MongoDB, читает Caffesta config из `caffesta_configs`
  2. Дёргает `export_sales_totals` за указанный день — показывает общие суммы и список терминалов
  3. Дёргает per-terminal `receipts_by_shift_day/{tid}/{date}` для каждого терминала — считает count и sum
  4. Печатает сравнительную таблицу, чтобы увидеть, какой терминал отдаёт сколько

Запуск на VPS (где крутится Menu_rest2):
    docker exec -it menu_rest2-backend-1 python /app/scripts/diagnose_caffesta_day.py 2026-06-13

Если backend-контейнер не запущен или /app/scripts/ нет в нём — копирните файл рядом:
    docker cp scripts/diagnose_caffesta_day.py menu_rest2-backend-1:/tmp/
    docker exec menu_rest2-backend-1 python /tmp/diagnose_caffesta_day.py 2026-06-13

Параметры:
    arg 1: дата YYYY-MM-DD (default = вчера по Минску)
    env  : MONGO_URL (default берёт из бэкенд /app/backend/.env)
"""
import os
import sys
import asyncio
import json
from datetime import datetime, timedelta, timezone

# Загружаем .env если рядом
try:
    from dotenv import load_dotenv
    for candidate in ("/app/backend/.env", os.path.join(os.path.dirname(__file__), "..", "backend", ".env")):
        if os.path.exists(candidate):
            load_dotenv(candidate)
            break
except ImportError:
    pass

try:
    import httpx
except ImportError:
    print("Нужен httpx: pip install httpx")
    sys.exit(1)

try:
    from motor.motor_asyncio import AsyncIOMotorClient
except ImportError:
    print("Нужен motor: pip install motor")
    sys.exit(1)


def yesterday_minsk_str() -> str:
    minsk = datetime.now(timezone.utc) + timedelta(hours=3)
    return (minsk.date() - timedelta(days=1)).strftime("%Y-%m-%d")


async def main():
    date = sys.argv[1] if len(sys.argv) > 1 else yesterday_minsk_str()
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    if not mongo_url or not db_name:
        print("ОШИБКА: MONGO_URL / DB_NAME не заданы. Запускайте внутри backend-контейнера или экспортируйте переменные.")
        sys.exit(2)

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    # Берём первый ресторан с включённым Caffesta (collection name: caffesta_config — без 's')
    cfg = await db.caffesta_config.find_one({"enabled": True})
    if not cfg:
        # Fallback: посмотреть вообще все, что есть
        any_cfg = await db.caffesta_config.find_one({})
        if any_cfg:
            print(f"Найден конфиг, но enabled != True. Используем его. Поля: {list(any_cfg.keys())}")
            cfg = any_cfg
        else:
            print("Caffesta-конфигурация не найдена в БД (collection caffesta_config).")
            sys.exit(3)

    account = cfg.get("account_name")
    api_key = cfg.get("api_key")
    configured_pos = cfg.get("pos_id")
    rid = cfg.get("restaurant_id")

    print("=" * 80)
    print(f"Дата:                {date}")
    print(f"Ресторан (id):       {rid}")
    print(f"Caffesta account:    {account}")
    print(f"Configured pos_id:   {configured_pos}")
    print("=" * 80)

    base = f"https://{account}.caffesta.com/a"
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30, headers=headers) as http:
        # 1) Per-terminal totals от Caffesta UI
        print("\n[1/3] export_sales_totals?add_gr_by=terminal_id — Caffesta UI per-terminal суммы")
        url = f"{base}/v1.0/product/export_sales_totals?start={date}&end={date}&add_gr_by=terminal_id"
        r = await http.get(url)
        data = r.json() if r.status_code == 200 else {}
        rows = data.get("data", []) if isinstance(data, dict) else []
        print(f"  HTTP {r.status_code}, rows={len(rows)}")
        terminal_ids = []
        for row in rows:
            tid = row.get("caf_terminal_id") or row.get("terminal_id")
            if tid:
                terminal_ids.append(int(tid))
            print(f"  • terminal_id={tid}  rows={json.dumps(row, ensure_ascii=False)[:200]}")
        terminal_ids = sorted(set(terminal_ids))

        # 2) Общий итог за день (без gr_by) — то, что показывает Caffesta UI
        print("\n[2/3] export_sales_totals (без gr_by) — общий итог дня по версии Caffesta")
        url2 = f"{base}/v1.0/product/export_sales_totals?start={date}&end={date}"
        r2 = await http.get(url2)
        data2 = r2.json() if r2.status_code == 200 else {}
        ui_rows = data2.get("data", []) if isinstance(data2, dict) else []
        print(f"  HTTP {r2.status_code}, rows={len(ui_rows)}")
        for row in ui_rows:
            print(f"  • {json.dumps(row, ensure_ascii=False)[:400]}")

        # 3) receipts_by_shift_day per terminal — то, что грузит наш digest
        print("\n[3/3] receipts_by_shift_day/{terminal_id}/{date} — то, что грузит наш digest")
        if not terminal_ids and configured_pos:
            terminal_ids = [int(configured_pos)]
            print(f"  (fallback на configured_pos_id={configured_pos})")
        if not terminal_ids:
            print("  Список терминалов пуст — нечего загружать.")
            return

        grand_count = 0
        grand_sum = 0.0
        grand_net = 0.0
        for tid in terminal_ids:
            url3 = f"{base}/v1.1/draft/receipts_by_shift_day/{tid}/{date}"
            r3 = await http.get(url3)
            try:
                d3 = r3.json()
            except Exception:
                d3 = None
            receipts = []
            if isinstance(d3, list):
                receipts = d3
            elif isinstance(d3, dict) and d3.get("success") and isinstance(d3.get("data"), list):
                receipts = d3["data"]
            count = sum(1 for r in receipts if int(r.get("income") or 1) > 0)
            gross = sum(float(r.get("total_sum", 0) or 0) for r in receipts)
            net = sum(int(r.get("income") or 1) * float(r.get("total_sum", 0) or 0) for r in receipts)
            grand_count += count
            grand_sum += gross
            grand_net += net
            print(f"  • term={tid}: HTTP {r3.status_code}  receipts_total={len(receipts)}  sales(income=1)={count}  gross={gross:.2f}  net_with_returns={net:.2f}")

        print("\n" + "=" * 80)
        print(f"ИТОГО digest (как у нас в Telegram):")
        print(f"   чеков:    {grand_count}")
        print(f"   gross:    {grand_sum:.2f}")
        print(f"   net:      {grand_net:.2f}  ← это значение и улетает в digest")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
