"""Parser for chef-supplied recipe text.

Input format (typical):

    Соус кукуруза п/ф
    Кукуруза зерно 1300
    Лук репка п/ф 300
    ...
    Выход 1000

    Паста с креветками
    Креветки п/ф 100
    Соль 5
    Соус кукуруза п/ф 150
    ...
    Выход 310

Multiple blocks separated by blank lines. Each block has:
- 1st non-empty line → title
- middle lines → "<ingredient name> <qty>[ <unit>]"
- last "Выход N" → yield in grams (optional)

We resolve every ingredient line to a catalog entry via fuzzy match
(RapidFuzz). Public API: `parse_recipe_text(text, catalog) -> dict`.
"""
from __future__ import annotations

import re
from typing import Optional

from rapidfuzz import fuzz, process


# --- Tokenization ---

_QTY_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*([а-яa-z]*)$", re.IGNORECASE)
_YIELD_RE = re.compile(r"^\s*в[ыi]?ход[\s:.\-]*\s*(\d+(?:[.,]\d+)?)\s*([а-яa-z]*)\s*$", re.IGNORECASE)


def _normalize(s: str) -> str:
    s = (s or "").strip()
    # Convert russian "ё" → "е" so fuzzy match doesn't punish it.
    s = s.replace("ё", "е").replace("Ё", "Е")
    return s


def _strip_marker(name: str) -> str:
    """Remove the «п/ф» marker from a name so it matches catalog entries
    that don't carry it. We keep the marker on the wire so the UI can show
    'this was a sub-product line' but match against the cleaner version."""
    s = _normalize(name)
    # п/ф can appear as "п/ф", "п\ф", "п.ф", "пф" — strip them all.
    s = re.sub(r"\bп\s*[/\\.]?\s*ф\b", "", s, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", s).strip()


def _split_blocks(text: str) -> list[list[str]]:
    """Split chef's message into blocks separated by blank lines."""
    blocks: list[list[str]] = []
    current: list[str] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            if current:
                blocks.append(current)
                current = []
            continue
        current.append(line)
    if current:
        blocks.append(current)
    return blocks


def _parse_line(line: str) -> Optional[tuple[str, float, str]]:
    """Try to parse '<name> <qty>[<unit>]'. Returns (name, qty, unit) or None."""
    m = _QTY_RE.search(line)
    if not m:
        return None
    qty_raw, unit = m.group(1), m.group(2) or ""
    name = line[: m.start()].strip(" -–—:•·.,")
    if not name:
        return None
    try:
        qty = float(qty_raw.replace(",", "."))
    except ValueError:
        return None
    return name, qty, unit.lower()


def _parse_block(lines: list[str]) -> Optional[dict]:
    """Convert one block into {title, yield_g, ingredients}. Returns None if
    the block doesn't look like a recipe (e.g. it's a free-text comment)."""
    if not lines:
        return None
    title = lines[0]
    yield_g: Optional[float] = None
    ingredients: list[dict] = []

    for line in lines[1:]:
        ym = _YIELD_RE.match(line)
        if ym:
            try:
                yield_g = float(ym.group(1).replace(",", "."))
            except ValueError:
                pass
            continue
        parsed = _parse_line(line)
        if not parsed:
            continue
        name, qty, unit = parsed
        ingredients.append({
            "name": name,
            "qty": qty,
            "unit": unit,
            "is_sub_product_hint": "п/ф" in line.lower() or "пф" in name.lower().split(),
        })

    if not ingredients:
        return None

    return {
        "title": title,
        "yield_g": yield_g,
        "ingredients": ingredients,
    }


# --- Catalog matching ---

def _build_choices(catalog: list[dict]) -> list[tuple[str, dict]]:
    """Build (normalized_name, original_entry) pairs for fuzzy lookup."""
    out = []
    for c in catalog or []:
        name = c.get("name") or ""
        if not name:
            continue
        norm = _strip_marker(name).lower()
        if norm:
            out.append((norm, c))
    return out


def _match_ingredient(name: str, choices: list[tuple[str, dict]], threshold: int = 75) -> Optional[dict]:
    """Find the best fuzzy match for `name` in catalog. Returns dict or None."""
    if not choices:
        return None
    norm = _strip_marker(name).lower()
    if not norm:
        return None

    # rapidfuzz expects a list of strings; we map back via index.
    names_only = [c[0] for c in choices]
    best = process.extractOne(norm, names_only, scorer=fuzz.WRatio, score_cutoff=threshold)
    if not best:
        return None
    _, score, idx = best
    entry = choices[idx][1]
    return {
        "match": entry,
        "confidence": int(score),
    }


def _unit_factor(unit: str) -> float:
    """Convert recipe unit to Caffesta's base unit (kg/l/pc).
    Defaults to 1.0 (no conversion) so the UI can override."""
    u = (unit or "").strip().lower()
    if u in {"г", "g", "грамм"}:
        return 0.001
    if u in {"мл", "ml"}:
        return 0.001
    if u in {"кг", "kg", "л", "l", "шт", "pc", "pcs"}:
        return 1.0
    # No unit given — chef typically writes weights in grams.
    return 0.001


def parse_recipe_text(text: str, catalog: list[dict]) -> dict:
    """Main entry point.

    catalog: items from /cost-catalog with keys:
        caffesta_product_id, name, self_cost, avgInvoicedSelfCost,
        is_sub_product, is_tech_card, is_local_subproduct (optional)

    Returns {
        "blocks": [
            {
                "kind": "subproduct" | "dish",  # heuristic: middle blocks are п/ф
                "title": str,
                "yield_g": float | None,
                "ingredients": [
                    {
                        "name": str,            # original from text
                        "qty": float,
                        "unit": str,
                        "unit_factor": float,
                        "matched": {            # null if no match
                            "caffesta_product_id": int | None,
                            "local_subproduct_id": str | None,
                            "name": str,
                            "type": str,
                            "self_cost": float,
                        } | None,
                        "confidence": int,
                    }
                ],
            }
        ],
        "stats": {"matched": int, "unmatched": int, "blocks": int}
    }
    """
    raw_blocks = _split_blocks(text or "")
    if not raw_blocks:
        return {"blocks": [], "stats": {"matched": 0, "unmatched": 0, "blocks": 0}}

    parsed: list[dict] = []
    for lines in raw_blocks:
        b = _parse_block(lines)
        if b:
            parsed.append(b)
    if not parsed:
        return {"blocks": [], "stats": {"matched": 0, "unmatched": 0, "blocks": 0}}

    # Heuristic: when there are 2+ blocks, the LAST one is the dish; earlier
    # ones are sub-products being defined inline. With a single block, it's
    # the dish (or a standalone п/ф — we let the UI decide).
    for i, b in enumerate(parsed):
        b["kind"] = "subproduct" if (len(parsed) > 1 and i < len(parsed) - 1) else "dish"

    choices = _build_choices(catalog or [])
    matched = unmatched = 0

    # Inline-defined sub-products from earlier blocks become available choices
    # for later blocks. We assign synthetic ids prefixed with "inline-N" so
    # the UI can later substitute them with real local_subproduct_ids when
    # the user clicks "Save".
    inline_choices: list[tuple[str, dict]] = []

    for i, block in enumerate(parsed):
        for ing in block["ingredients"]:
            ing["unit_factor"] = _unit_factor(ing["unit"])
            # Inline sub-products win first — повар явно их сейчас определил.
            hit = _match_ingredient(ing["name"], inline_choices, threshold=70)
            if not hit:
                hit = _match_ingredient(ing["name"], choices)
            if hit:
                m = hit["match"]
                ing["matched"] = {
                    "caffesta_product_id": m.get("caffesta_product_id"),
                    "local_subproduct_id": m.get("local_subproduct_id"),
                    "inline_subproduct_index": m.get("_inline_index"),
                    "name": m.get("name"),
                    "type": ("local_subproduct" if m.get("local_subproduct_id")
                             else "inline_subproduct" if m.get("_inline_index") is not None
                             else "sub_product" if m.get("is_sub_product")
                             else "tech_card" if m.get("is_tech_card")
                             else "product"),
                    "self_cost": float(m.get("self_cost") or m.get("avgInvoicedSelfCost") or 0),
                }
                ing["confidence"] = hit["confidence"]
                matched += 1
            else:
                ing["matched"] = None
                ing["confidence"] = 0
                unmatched += 1

        # If this block is a sub-product, register it for later blocks.
        if block["kind"] == "subproduct" and block.get("yield_g"):
            # Self-cost will be computed by the UI/backend after persisting.
            inline_entry = {
                "name": block["title"],
                "_inline_index": i,
                "self_cost": 0,  # placeholder — frontend recomputes
                "is_inline": True,
            }
            inline_choices.append((_strip_marker(block["title"]).lower(), inline_entry))

    return {
        "blocks": parsed,
        "stats": {"matched": matched, "unmatched": unmatched, "blocks": len(parsed)},
    }
