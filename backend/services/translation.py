"""Lightweight RU→EN translation for menu content.

Uses Gemini flash via emergentintegrations.
- `translate_ru_to_en(text)` — fail-silent, returns "" so the caller can fall back to RU.
- `translate_ru_to_en_strict(text)` — raises on errors so endpoints can surface the real cause.

Caching:
A persistent MongoDB-backed cache (`translation_cache` collection) deduplicates LLM
calls for repeated dish names like "Капучино" or "Карбонара". Keys are normalized
(lowercase + trimmed) so "  Капучино  " and "капучино" hit the same entry.
A small built-in seed dictionary covers common menu words to avoid the first
LLM call for ubiquitous items.
"""
import os
import logging
import uuid
import asyncio

from database import db

log = logging.getLogger(__name__)

CACHE_COLLECTION = "translation_cache"

# Pre-seeded common menu translations. Inserted on first miss so we save tokens
# from day 1. Keep it short; the cache grows organically with each new translation.
SEED_DICTIONARY = {
    # Drinks
    "эспрессо": "Espresso",
    "капучино": "Cappuccino",
    "латте": "Latte",
    "американо": "Americano",
    "раф": "Raf coffee",
    "флэт уайт": "Flat white",
    "какао": "Cocoa",
    "горячий шоколад": "Hot chocolate",
    "чёрный чай": "Black tea",
    "зелёный чай": "Green tea",
    "лимонад": "Lemonade",
    "морс": "Berry juice",
    "сок": "Juice",
    "вода": "Still water",
    "вода газированная": "Sparkling water",
    "пиво": "Beer",
    "вино красное": "Red wine",
    "вино белое": "White wine",
    "просекко": "Prosecco",
    "шампанское": "Champagne",
    # Food categories
    "завтраки": "Breakfast",
    "закуски": "Starters",
    "салаты": "Salads",
    "супы": "Soups",
    "паста": "Pasta",
    "пицца": "Pizza",
    "бургеры": "Burgers",
    "стейки": "Steaks",
    "гарниры": "Sides",
    "десерты": "Desserts",
    "напитки": "Drinks",
    "кофе": "Coffee",
    "чай": "Tea",
    "вино": "Wine",
    "бар": "Bar",
    "кухня": "Kitchen",
    # Frequent dishes
    "борщ": "Borscht",
    "пельмени": "Pelmeni",
    "вареники": "Vareniki",
    "блины": "Pancakes",
    "сырники": "Syrniki",
    "оладьи": "Oladyi pancakes",
    "цезарь": "Caesar salad",
    "цезарь с курицей": "Caesar salad with chicken",
    "греческий салат": "Greek salad",
    "оливье": "Olivier salad",
    "карбонара": "Carbonara",
    "болоньезе": "Bolognese",
    "лазанья": "Lasagna",
    "ризотто": "Risotto",
    "том ям": "Tom yum",
    "том ям с креветками": "Tom yum with shrimp",
    "грибной крем-суп": "Mushroom cream soup",
    "чизкейк": "Cheesecake",
    "тирамису": "Tiramisu",
    "наполеон": "Napoleon cake",
    "медовик": "Honey cake",
    "брускетта": "Bruschetta",
    "сырная тарелка": "Cheese platter",
    "мясная тарелка": "Cold cuts platter",
    # Common modifiers
    "острое": "Spicy",
    "новинка": "New",
    "хит": "Bestseller",
}


def _normalize(text: str) -> str:
    """Cache key: lowercase + collapsed whitespace. Keeps original punctuation
    so 'Цезарь, лёгкий' ≠ 'Цезарь лёгкий' — translations may differ."""
    return " ".join((text or "").strip().split()).lower()


_seed_done = False


async def _ensure_indexes_and_seed() -> None:
    """One-shot: create unique index on `key_ru` and load the seed dictionary
    if the cache is empty. Cheap on subsequent calls (boolean guard)."""
    global _seed_done
    if _seed_done:
        return
    try:
        await db[CACHE_COLLECTION].create_index("key_ru", unique=True)
        existing = await db[CACHE_COLLECTION].count_documents({})
        if existing == 0 and SEED_DICTIONARY:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat()
            await db[CACHE_COLLECTION].insert_many([
                {"key_ru": _normalize(ru), "translation": en, "source": "seed", "created_at": now}
                for ru, en in SEED_DICTIONARY.items()
            ])
            log.info("translation_cache seeded with %d entries", len(SEED_DICTIONARY))
    except Exception as e:
        log.warning("translation_cache init failed: %s", e)
    _seed_done = True


async def cache_get(text: str) -> str | None:
    """Return cached translation or None."""
    await _ensure_indexes_and_seed()
    key = _normalize(text)
    if not key:
        return None
    try:
        doc = await db[CACHE_COLLECTION].find_one({"key_ru": key}, {"_id": 0, "translation": 1})
    except Exception as e:
        log.warning("cache_get error: %s", e)
        return None
    if doc and doc.get("translation"):
        return doc["translation"]
    return None


async def cache_put(text: str, translation: str, source: str = "llm") -> None:
    """Upsert translation into the cache. Silent on errors."""
    if not translation:
        return
    key = _normalize(text)
    if not key:
        return
    try:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        await db[CACHE_COLLECTION].update_one(
            {"key_ru": key},
            {"$set": {"translation": translation, "source": source, "updated_at": now},
             "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
    except Exception as e:
        log.warning("cache_put error: %s", e)


async def _llm_translate(text: str, max_retries: int = 3) -> str:
    """Raw LLM call — raises on errors. Used by both strict and silent variants."""
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise RuntimeError("EMERGENT_LLM_KEY is not set in backend env")

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except ImportError as e:
        raise RuntimeError(f"emergentintegrations not installed: {e}") from e

    system_message = (
        "You are a professional menu translator. Translate the given Russian restaurant "
        "menu text into natural, concise English suitable for a tourist-friendly menu. "
        "Preserve proper nouns (dish names like 'Borscht', 'Pelmeni'), keep the tone neutral "
        "and appetizing. Do NOT add explanations, quotes, markdown, or punctuation that "
        "wasn't in the original. Return ONLY the translated text, nothing else."
    )

    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            chat = LlmChat(
                api_key=api_key,
                session_id=f"menu-tr-{uuid.uuid4()}",
                system_message=system_message,
            ).with_model("gemini", "gemini-2.5-flash")

            resp = await chat.send_message(UserMessage(text=text.strip()))
            if resp:
                out = resp.strip().strip('"').strip("'")
                if len(out) > max(200, len(text) * 4):
                    out = out[: max(200, len(text) * 4)]
                if out:
                    return out
            last_err = RuntimeError("LLM returned empty response")
        except Exception as e:
            last_err = e
        if attempt < max_retries - 1:
            await asyncio.sleep(0.5 * (attempt + 1))

    raise last_err or RuntimeError("LLM translation failed after retries")


async def _do_translate(text: str, max_retries: int = 3, use_cache: bool = True) -> str:
    """Cache-aware translator. Raises on LLM errors so the strict variant
    can propagate them. Cache hits never fail."""
    if not text or not text.strip():
        return ""

    if use_cache:
        cached = await cache_get(text)
        if cached:
            return cached

    out = await _llm_translate(text, max_retries=max_retries)
    if use_cache:
        await cache_put(text, out, source="llm")
    return out


async def translate_ru_to_en(text: str, use_cache: bool = True) -> str:
    """Fail-silent variant for background tasks: returns "" on error."""
    try:
        return await _do_translate(text, use_cache=use_cache)
    except Exception as e:
        log.warning("translate_ru_to_en failed: %s", e)
        return ""


async def translate_ru_to_en_strict(text: str, use_cache: bool = True) -> str:
    """Strict variant: raises on error. Use in pre-flight checks where the
    caller wants to report the real cause to the user."""
    return await _do_translate(text, use_cache=use_cache)


async def get_cache_stats() -> dict:
    """Lightweight stats for diagnostic UI."""
    await _ensure_indexes_and_seed()
    try:
        total = await db[CACHE_COLLECTION].count_documents({})
        seeded = await db[CACHE_COLLECTION].count_documents({"source": "seed"})
        llm = await db[CACHE_COLLECTION].count_documents({"source": "llm"})
        manual = await db[CACHE_COLLECTION].count_documents({"source": "manual"})
        return {"total": total, "seed": seeded, "llm": llm, "manual": manual}
    except Exception as e:
        log.warning("get_cache_stats error: %s", e)
        return {"total": 0, "seed": 0, "llm": 0, "manual": 0, "error": str(e)}
