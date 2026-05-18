"""
Регрессия для бага: импортёр Lunchpad терял позиции, лежащие на 3-м уровне
вложенности (Барное меню → Пиво → Разливное пиво → бутылки).

До фикса: парсер обрабатывал только 2 уровня (category → subcategory) и при
встрече вложенной type=0 внутри subcategory её sub_items_raw фильтровались
условием `type != 4` — что выкидывало все позиции.

После фикса: парсер рекурсивно сплющивает дерево любой глубины в плоский
список категорий с конкатенированными именами ("A — B — C").
"""

import os
import sys
from dotenv import load_dotenv

# Загружаем env до импорта модулей, которые используют MONGO_URL
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from routes.menu import parse_lunchpad_data


def _make_dish(name, price=10, weight="100g"):
    return {
        "type": 4,
        "name": name,
        "description": "",
        "prices": [{"price": price, "measure": weight}],
        "foto": {"image_url": ""},
        "in_stop_list": False,
    }


def _make_cat(name, items, type_=0):
    return {
        "type": type_,
        "name": name,
        "display": "grid",
        "items": items,
        "foto": {"image_url": ""},
    }


def test_3_level_nesting_extracts_all_dishes():
    """Барное меню → Пиво → Разливное → [бутылки type=4] — раньше терялось."""
    raw = [
        _make_cat("Барное меню", [
            _make_cat("Пиво (Beer)", [
                _make_cat("Разливное пиво", [
                    _make_dish("Tuborg 0.3", 5, "300мл"),
                    _make_dish("Tuborg 0.5", 8, "500мл"),
                ]),
                _make_cat("Бутылочное пиво", [
                    _make_dish("Corona", 13, "330мл"),
                ]),
            ]),
        ]),
    ]
    out = parse_lunchpad_data(raw)
    cat_names = [c['name'] for c in out['categories']]

    # Родительская «оболочечная» категория без собственных блюд НЕ создаётся
    assert "Барное меню" not in cat_names, "Пустая родительская категория не должна создаваться"
    assert "Барное меню — Пиво (Beer) — Разливное пиво" in cat_names
    assert "Барное меню — Пиво (Beer) — Бутылочное пиво" in cat_names

    draft = next(c for c in out['categories'] if c['name'].endswith("Разливное пиво"))
    assert len(draft['items']) == 2
    assert {i['name'] for i in draft['items']} == {"Tuborg 0.3", "Tuborg 0.5"}

    bottled = next(c for c in out['categories'] if c['name'].endswith("Бутылочное пиво"))
    assert len(bottled['items']) == 1
    assert bottled['items'][0]['name'] == "Corona"
    assert bottled['items'][0]['price'] == 13.0


def test_2_level_nesting_still_works():
    """Базовый случай: category → [items type=4] — должен работать как раньше."""
    raw = [
        _make_cat("Салаты", [
            _make_dish("Цезарь", 18, "200г"),
            _make_dish("Греческий", 16, "230г"),
        ]),
    ]
    out = parse_lunchpad_data(raw)
    assert len(out['categories']) == 1
    cat = out['categories'][0]
    assert cat['name'] == "Салаты"
    assert len(cat['items']) == 2


def test_mixed_level_dishes_and_subcat():
    """Категория с прямыми блюдами + одной подкатегорией: создаётся 2 категории."""
    raw = [
        _make_cat("Завтраки", [
            _make_dish("Сырники", 12, "200г"),
            _make_dish("Омлет", 10, "150г"),
            _make_cat("Добавки", [
                _make_dish("Сметана", 2, "30г"),
                _make_dish("Варенье", 3, "30г"),
            ]),
        ]),
    ]
    out = parse_lunchpad_data(raw)
    names = [c['name'] for c in out['categories']]
    assert "Завтраки" in names
    assert "Завтраки — Добавки" in names

    main = next(c for c in out['categories'] if c['name'] == "Завтраки")
    assert {i['name'] for i in main['items']} == {"Сырники", "Омлет"}

    sub = next(c for c in out['categories'] if c['name'] == "Завтраки — Добавки")
    assert {i['name'] for i in sub['items']} == {"Сметана", "Варенье"}


def test_html_stripped_from_names_recursively():
    raw = [
        _make_cat("<p>Бар</p>", [
            _make_cat("<b>Вина</b>", [
                _make_dish("<i>Merlot</i>", 15, "125мл"),
            ]),
        ]),
    ]
    out = parse_lunchpad_data(raw)
    cat = out['categories'][0]
    assert cat['name'] == "Бар — Вина"
    assert cat['items'][0]['name'] == "Merlot"


def test_real_sample_file_full_extraction():
    """Если в окружении есть файл /tmp/menu5.data — проверяем количество позиций."""
    sample = "/tmp/menu5.data"
    if not os.path.exists(sample):
        return  # пропускаем, если файла нет
    import json
    raw = json.load(open(sample, encoding='utf-8'))
    out = parse_lunchpad_data(raw)
    total_dishes = sum(
        len([i for i in c['items'] if not i.get('is_banner')])
        for c in out['categories']
    )
    assert total_dishes == 400, f"Ожидалось 400 type=4 блюд, получено {total_dishes}"

    # И ключевые подкатегории действительно появились
    cat_names = [c['name'] for c in out['categories']]
    assert any("Пиво (Beer) — Разливное" in n for n in cat_names)
    assert any("Пиво (Beer) — Бутылочное" in n for n in cat_names)
    assert any("Вино красное" in n for n in cat_names)
    assert any("Вино белое" in n for n in cat_names)
    assert any("Виски" in n for n in cat_names)


if __name__ == "__main__":
    test_3_level_nesting_extracts_all_dishes()
    test_2_level_nesting_still_works()
    test_mixed_level_dishes_and_subcat()
    test_html_stripped_from_names_recursively()
    test_real_sample_file_full_extraction()
    print("OK — все 5 тестов прошли")
