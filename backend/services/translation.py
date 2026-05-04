"""RU → EN / ZH translation for menu content.

Uses Gemini flash via emergentintegrations.

Public functions:
- `translate_ru_to(text, target_lang)` — fail-silent, returns "" on error.
- `translate_ru_to_strict(text, target_lang)` — raises on errors.
- Convenience wrappers `translate_ru_to_en(text)` and `translate_ru_to_zh(text)`.

Caching:
A persistent MongoDB-backed cache (`translation_cache` collection) deduplicates LLM
calls. Compound key = (key_ru, lang). A small built-in seed dictionary covers
common menu words for EN to avoid the first LLM call for ubiquitous items.
"""
import os
import logging
import uuid
import asyncio

from database import db

log = logging.getLogger(__name__)

CACHE_COLLECTION = "translation_cache"

SUPPORTED_LANGS = {"en", "zh"}

# Pre-seeded common menu translations for EN. Inserted on first miss.
SEED_DICTIONARY_EN = {
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

# System prompt per target language. Keep them tight — long instructions
# eat tokens and reduce reliability.
SYSTEM_PROMPTS = {
    "en": (
        "You are a professional menu translator. Translate the given Russian restaurant "
        "menu text into natural, concise English suitable for a tourist-friendly menu. "
        "Preserve proper nouns (dish names like 'Borscht', 'Pelmeni'), keep the tone neutral "
        "and appetizing. Do NOT add explanations, quotes, markdown, or punctuation that "
        "wasn't in the original. Return ONLY the translated text, nothing else."
    ),
    "zh": (
        "你是一位专业的餐厅菜单翻译。请将给定的俄语菜单文本翻译成简体中文（中国大陆使用），"
        "适合中国游客阅读的自然、简洁的中文。保留专有名词的标准中文译法（如「罗宋汤」「俄式饺子」等）。"
        "保持中性、令人有食欲的语气。不要添加任何解释、引号、Markdown 或原文中没有的标点符号。"
        "只返回翻译后的文本，不要返回任何其他内容。"
    ),
}


def _normalize(text: str) -> str:
    return " ".join((text or "").strip().split()).lower()


_seed_done = False


async def _ensure_indexes_and_seed() -> None:
    """Idempotent: build compound (key_ru, lang) unique index and seed EN dictionary.
    Migrates legacy entries (lang missing → 'en')."""
    global _seed_done
    if _seed_done:
        return
    try:
        # Migrate legacy entries lacking `lang` field — they were all RU→EN.
        await db[CACHE_COLLECTION].update_many(
            {"lang": {"$exists": False}},
            {"$set": {"lang": "en"}},
        )
        # Drop old single-field unique index (if present) and create compound.
        try:
            existing = await db[CACHE_COLLECTION].index_information()
            for name, info in existing.items():
                keys = info.get("key", [])
                if len(keys) == 1 and keys[0][0] == "key_ru" and info.get("unique"):
                    await db[CACHE_COLLECTION].drop_index(name)
                    log.info("translation_cache: dropped legacy unique index '%s'", name)
        except Exception as e:
            log.warning("translation_cache: legacy index check failed: %s", e)

        await db[CACHE_COLLECTION].create_index(
            [("key_ru", 1), ("lang", 1)], unique=True
        )

        # Seed EN dictionary if empty for that lang.
        en_count = await db[CACHE_COLLECTION].count_documents({"lang": "en", "source": "seed"})
        if en_count == 0 and SEED_DICTIONARY_EN:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat()
            try:
                await db[CACHE_COLLECTION].insert_many([
                    {"key_ru": _normalize(ru), "lang": "en", "translation": en,
                     "source": "seed", "created_at": now}
                    for ru, en in SEED_DICTIONARY_EN.items()
                ], ordered=False)
                log.info("translation_cache: seeded %d EN entries", len(SEED_DICTIONARY_EN))
            except Exception as e:
                # Duplicates from prior runs — fine, ignore.
                log.info("translation_cache: seed skipped/partial: %s", e)
    except Exception as e:
        log.warning("translation_cache init failed: %s", e)
    _seed_done = True


async def cache_get(text: str, lang: str) -> str | None:
    await _ensure_indexes_and_seed()
    key = _normalize(text)
    if not key or lang not in SUPPORTED_LANGS:
        return None
    try:
        doc = await db[CACHE_COLLECTION].find_one(
            {"key_ru": key, "lang": lang},
            {"_id": 0, "translation": 1},
        )
    except Exception as e:
        log.warning("cache_get error: %s", e)
        return None
    if doc and doc.get("translation"):
        return doc["translation"]
    return None


async def cache_put(text: str, translation: str, lang: str, source: str = "llm") -> None:
    if not translation or lang not in SUPPORTED_LANGS:
        return
    key = _normalize(text)
    if not key:
        return
    try:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        await db[CACHE_COLLECTION].update_one(
            {"key_ru": key, "lang": lang},
            {"$set": {"translation": translation, "source": source, "updated_at": now},
             "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
    except Exception as e:
        log.warning("cache_put error: %s", e)


async def _llm_translate(text: str, lang: str, max_retries: int = 3) -> str:
    """Raw LLM call — raises on errors."""
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise RuntimeError("EMERGENT_LLM_KEY is not set in backend env")
    if lang not in SYSTEM_PROMPTS:
        raise ValueError(f"Unsupported translation language: {lang}")

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except ImportError as e:
        raise RuntimeError(f"emergentintegrations not installed: {e}") from e

    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            chat = LlmChat(
                api_key=api_key,
                session_id=f"menu-tr-{lang}-{uuid.uuid4()}",
                system_message=SYSTEM_PROMPTS[lang],
            ).with_model("gemini", "gemini-2.5-flash")

            resp = await chat.send_message(UserMessage(text=text.strip()))
            if resp:
                out = resp.strip().strip('"').strip("'")
                # Bound length: Chinese text is more compact, so allow slightly less
                cap = max(200, len(text) * 4)
                if len(out) > cap:
                    out = out[:cap]
                if out:
                    return out
            last_err = RuntimeError("LLM returned empty response")
        except Exception as e:
            last_err = e
        if attempt < max_retries - 1:
            await asyncio.sleep(0.5 * (attempt + 1))

    raise last_err or RuntimeError("LLM translation failed after retries")


async def _do_translate(text: str, lang: str, max_retries: int = 3, use_cache: bool = True) -> str:
    if not text or not text.strip():
        return ""
    if lang not in SUPPORTED_LANGS:
        raise ValueError(f"Unsupported language: {lang}")

    if use_cache:
        cached = await cache_get(text, lang)
        if cached:
            return cached

    out = await _llm_translate(text, lang, max_retries=max_retries)
    if use_cache:
        await cache_put(text, out, lang, source="llm")
    return out


# ============ Public API ============

async def translate_ru_to(text: str, target_lang: str, use_cache: bool = True) -> str:
    """Fail-silent: returns "" on any error."""
    try:
        return await _do_translate(text, target_lang, use_cache=use_cache)
    except Exception as e:
        log.warning("translate_ru_to(%s) failed: %s", target_lang, e)
        return ""


async def translate_ru_to_strict(text: str, target_lang: str, use_cache: bool = True) -> str:
    """Raises on errors. Use in pre-flight smoke tests."""
    return await _do_translate(text, target_lang, use_cache=use_cache)


# ---- Backward-compat thin wrappers ----

async def translate_ru_to_en(text: str, use_cache: bool = True) -> str:
    return await translate_ru_to(text, "en", use_cache=use_cache)


async def translate_ru_to_en_strict(text: str, use_cache: bool = True) -> str:
    return await translate_ru_to_strict(text, "en", use_cache=use_cache)


async def translate_ru_to_zh(text: str, use_cache: bool = True) -> str:
    return await translate_ru_to(text, "zh", use_cache=use_cache)


async def translate_ru_to_zh_strict(text: str, use_cache: bool = True) -> str:
    return await translate_ru_to_strict(text, "zh", use_cache=use_cache)


async def get_cache_stats() -> dict:
    await _ensure_indexes_and_seed()
    try:
        out = {"total": await db[CACHE_COLLECTION].count_documents({})}
        for lang in SUPPORTED_LANGS:
            out[lang] = await db[CACHE_COLLECTION].count_documents({"lang": lang})
        out["seed"] = await db[CACHE_COLLECTION].count_documents({"source": "seed"})
        out["llm"] = await db[CACHE_COLLECTION].count_documents({"source": "llm"})
        out["manual"] = await db[CACHE_COLLECTION].count_documents({"source": "manual"})
        return out
    except Exception as e:
        log.warning("get_cache_stats error: %s", e)
        return {"total": 0, "error": str(e)}


# Suffix → field name helper for routes/menu.py background tasks.
def lang_suffix(lang: str) -> str:
    """Return suffix used in DB fields. ZH → '_zh', EN → '_en', etc."""
    return f"_{lang}"
