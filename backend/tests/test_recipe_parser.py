"""Regression tests for chef recipe parser."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.recipe_parser import parse_recipe_text


CATALOG = [
    {"caffesta_product_id": 1, "name": "Кукуруза зерно консервированная", "self_cost": 5.5},
    {"caffesta_product_id": 2, "name": "Молоко 3.2%", "self_cost": 2.2},
    {"caffesta_product_id": 3, "name": "Соль", "self_cost": 0.5},
    {"caffesta_product_id": 4, "name": "Сахар-песок", "self_cost": 1.8},
    {"caffesta_product_id": 5, "name": "Креветки очищенные", "self_cost": 35.0, "is_sub_product": True},
    {"caffesta_product_id": 6, "name": "Перец черный горошек", "self_cost": 12.0},
    {"caffesta_product_id": 7, "name": "Масло подсолнечное", "self_cost": 4.3},
    {"caffesta_product_id": 10, "name": "Паста спагетти отварная", "self_cost": 6.0, "is_sub_product": True},
]


def test_parses_two_block_message():
    text = """Соус кукуруза п/ф
Кукуруза зерно 1300
Молоко 300
Соль 10
Сахар 20
Выход 1000

Паста с креветками
Креветки п/ф 100
Соль 5
Перец черный горох 1
Масло растительное 30
Соус кукуруза п/ф 150
Паста отварная п/ф 150
Выход 310"""

    res = parse_recipe_text(text, CATALOG)
    assert res["stats"]["blocks"] == 2
    assert res["blocks"][0]["kind"] == "subproduct"
    assert res["blocks"][1]["kind"] == "dish"
    assert res["blocks"][0]["title"] == "Соус кукуруза п/ф"
    assert res["blocks"][0]["yield_g"] == 1000.0
    assert res["blocks"][1]["yield_g"] == 310.0

    # Inline sub-product gets matched in dish block (not the raw "Кукуруза зерно").
    dish = res["blocks"][1]
    soup_line = next(i for i in dish["ingredients"] if "Соус кукуруза" in i["name"])
    assert soup_line["matched"]["type"] == "inline_subproduct"
    assert soup_line["matched"]["inline_subproduct_index"] == 0


def test_unit_factor_default_is_grams():
    text = "Тест блюдо\nСоль 5\nВыход 100"
    res = parse_recipe_text(text, CATALOG)
    assert res["blocks"][0]["ingredients"][0]["unit_factor"] == 0.001


def test_yo_normalization():
    text = "Тест\nЧёрный перец 5\nВыход 5"
    cat = [{"caffesta_product_id": 99, "name": "Черный перец молотый", "self_cost": 1}]
    res = parse_recipe_text(text, cat)
    ing = res["blocks"][0]["ingredients"][0]
    assert ing["matched"] is not None
    assert ing["matched"]["caffesta_product_id"] == 99


def test_empty_text_returns_empty():
    res = parse_recipe_text("", CATALOG)
    assert res["stats"]["blocks"] == 0
    assert res["blocks"] == []


def test_single_block_is_dish():
    text = "Цезарь с курицей\nКурица 100\nСалат 50\nВыход 200"
    res = parse_recipe_text(text, CATALOG)
    assert res["stats"]["blocks"] == 1
    assert res["blocks"][0]["kind"] == "dish"


if __name__ == "__main__":
    test_parses_two_block_message()
    test_unit_factor_default_is_grams()
    test_yo_normalization()
    test_empty_text_returns_empty()
    test_single_block_is_dish()
    print("All tests passed ✓")
