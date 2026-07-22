"""
Парсинг .docx с таблицами БЖУ и fuzzy-match с существующими MenuItem.

Ожидаемый формат таблицы:
  | Название блюда | Белки | Жиры | Углеводы | Ккал | кДж |
  | Сырники ...    | 11,15 | 16,37| 28,74    | 306  | 1285|

Заголовок строки может быть в первой строке таблицы (тогда пропускаем) или
отсутствовать (тогда каждая строка — блюдо). Определяем по типу первой ячейки:
если text не парсится как float в колонках 2..N — считаем заголовком.

Числовые значения могут содержать запятую вместо точки и завершаться единицами
измерения ("г", "ккал"). Всё сводится к float.
"""
from __future__ import annotations

import io
import re
from typing import Optional

from docx import Document
from rapidfuzz import fuzz, process


_NUM_RE = re.compile(r"[\d]+[.,]?[\d]*")


def _parse_number(cell: str) -> Optional[float]:
    """Возвращает float или None. Заменяет запятую на точку, вырезает единицы."""
    if cell is None:
        return None
    s = str(cell).strip()
    if not s:
        return None
    m = _NUM_RE.search(s.replace(",", "."))
    if not m:
        return None
    try:
        return float(m.group())
    except ValueError:
        return None


def _row_looks_like_header(cells: list[str]) -> bool:
    """Заголовок — если во 2-й/3-й/... ячейке текст, а не число."""
    if len(cells) < 4:
        return False
    for c in cells[1:6]:  # первые 5 числовых колонок
        if _parse_number(c) is not None:
            return False
    return True


def _clean_name(name: str) -> str:
    """Нормализация имени для матчинга: strip, замена nbsp и множественных пробелов."""
    if not name:
        return ""
    n = name.replace("\xa0", " ").replace("\u2013", "-").replace("\u2014", "-")
    n = re.sub(r"\s+", " ", n).strip()
    return n


def parse_docx_nutrition(file_bytes: bytes) -> list[dict]:
    """
    Парсит все таблицы docx и возвращает список записей:
      [{name, protein, fat, carbs, kcal, kj}].

    Формат таблицы (наблюдаемый в файле пользователя):
        row0 (merged): «Название блюда»
        row1 (merged): «Количество в 100 граммах»  ← подпись, игнорируем
        row2: [Белки, Жиры, Углеводы, Килокалории, Килоджоули]  ← заголовки
        row3: [11.15, 16.37, 28.74, 306.92, 1285.01]              ← значения

    Также поддерживается «плоский» формат — одна таблица со многими строками:
        row0: [Название, Белки, Жиры, Углеводы, Ккал, кДж]
        rowN: [Сырники, 11.15, 16.37, 28.74, 306.92, 1285.01]

    Строки без числовых значений (заголовки, разделители) пропускаются.
    """
    doc = Document(io.BytesIO(file_bytes))
    records: list[dict] = []
    seen_keys: set[str] = set()

    for table in doc.tables:
        # Формат №1 — «одно блюдо на таблицу»: 3-5 строк, первая строка = имя,
        # последняя строка = значения по 5 колонкам.
        if 3 <= len(table.rows) <= 5:
            name = _clean_name(table.rows[0].cells[0].text)
            last_row = table.rows[-1]
            value_cells = [c.text for c in last_row.cells]
            nums = _extract_5_values(value_cells)
            if name and any(v is not None for v in nums):
                key = name.lower()
                if key not in seen_keys:
                    seen_keys.add(key)
                    records.append(_record_from_name_and_nums(name, nums))
                continue

        # Формат №2 — «плоская таблица со строками»: >5 строк, первая = заголовок,
        # каждая следующая — имя + значения.
        for row in table.rows:
            cells = [c.text for c in row.cells]
            if len(cells) < 2:
                continue
            if _row_looks_like_header(cells):
                continue
            name = _clean_name(cells[0])
            if not name:
                continue
            nums = _extract_5_values(cells[1:6])
            if all(v is None for v in nums):
                continue
            key = name.lower()
            if key in seen_keys:
                continue
            seen_keys.add(key)
            records.append(_record_from_name_and_nums(name, nums))

    return records


def _extract_5_values(cells: list[str]) -> list[Optional[float]]:
    """Возвращает [protein, fat, carbs, kcal, kj] из списка ячеек.
    В merged-таблицах может быть больше 5 клеток (те же значения продублированы),
    поэтому берём уникальные подряд идущие числовые значения."""
    seen_vals: list[Optional[float]] = []
    prev = None
    for c in cells:
        v = _parse_number(c)
        # Skip duplicated adjacent cells (merged cells эмулируются повтором)
        if v is None:
            if prev is None:
                continue
            # Ноль пропускаем только если это НЕ настоящий 0 — но парсер выше
            # возвращает None для пустых. Здесь v is None означает "мусор".
            continue
        if seen_vals and seen_vals[-1] is not None and abs(seen_vals[-1] - v) < 1e-9 and prev == v:
            # Повтор от merged-cell
            continue
        seen_vals.append(v)
        prev = v
        if len(seen_vals) >= 5:
            break
    # Дополняем до 5
    while len(seen_vals) < 5:
        seen_vals.append(None)
    return seen_vals[:5]


def _record_from_name_and_nums(name: str, nums: list[Optional[float]]) -> dict:
    return {
        "name": name,
        "protein": nums[0],
        "fat": nums[1],
        "carbs": nums[2],
        "kcal": nums[3],
        "kj": nums[4],
    }


def match_records_to_items(
    records: list[dict],
    items: list[dict],
    score_threshold: int = 65,
    ambiguity_gap: int = 8,
) -> dict:
    """
    Для каждой записи из docx находит лучший MenuItem по имени.

    Scorer: комбинация token_set_ratio (устойчива к перестановке и разной длине)
    + partial_ratio (ловит подстроки). Итоговый score = max(token_set_ratio,
    partial_ratio − 5). Такой подход даёт стабильные оценки для русских
    многословных названий блюд и не завышает score из-за общих коротких слов
    вроде «с», «и», «а», как это делает WRatio.
    """
    if not items:
        return {"matched": [], "ambiguous": [], "unmatched": [
            {"source": r["name"], "values": _values_dict(r), "best_score": 0}
            for r in records
        ]}

    choices = [_clean_name(it["name"]).lower() for it in items]

    def _score(a: str, b: str, **_kwargs) -> float:
        ts = fuzz.token_set_ratio(a, b)
        pr = fuzz.partial_ratio(a, b) - 5  # slight penalty against pure substring
        return max(ts, pr)

    matched, ambiguous, unmatched = [], [], []
    for rec in records:
        query = _clean_name(rec["name"]).lower()
        if not query:
            continue

        top = process.extract(query, choices, scorer=_score, limit=3)
        if not top:
            unmatched.append({"source": rec["name"], "values": _values_dict(rec), "best_score": 0})
            continue

        best_name, best_score, best_idx = top[0]
        second_score = top[1][1] if len(top) > 1 else 0

        if best_score < score_threshold:
            unmatched.append({"source": rec["name"], "values": _values_dict(rec), "best_score": int(best_score)})
            continue

        best_item = items[best_idx]
        if best_score - second_score < ambiguity_gap and len(top) > 1:
            candidates = [
                {"item_id": items[idx]["id"], "name": items[idx]["name"], "score": int(sc)}
                for _, sc, idx in top if sc >= score_threshold
            ]
            ambiguous.append({
                "source": rec["name"],
                "candidates": candidates,
                "values": _values_dict(rec),
            })
        else:
            matched.append({
                "source": rec["name"],
                "item_id": best_item["id"],
                "item_name": best_item["name"],
                "score": int(best_score),
                "values": _values_dict(rec),
            })

    return {"matched": matched, "ambiguous": ambiguous, "unmatched": unmatched}


def _values_dict(rec: dict) -> dict:
    """Приводит запись к финальному виду для API/UI."""
    return {
        "protein": rec.get("protein"),
        "fat": rec.get("fat"),
        "carbs": rec.get("carbs"),
        "kcal": rec.get("kcal"),
        "kj": rec.get("kj"),
    }
