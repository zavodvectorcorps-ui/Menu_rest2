"""Lightweight RU→EN translation for menu content.

Uses Gemini flash-lite (cheapest/fastest) via emergentintegrations.
Fails silently — if translation can't be produced, empty string is returned so
the caller can fall back to the original RU text.
"""
import os
import logging
import uuid

log = logging.getLogger(__name__)


async def translate_ru_to_en(text: str) -> str:
    """Translate Russian text to English.
    Returns empty string on error (caller must fall back to original)."""
    if not text or not text.strip():
        return ""

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        log.warning("translate_ru_to_en: EMERGENT_LLM_KEY is not set")
        return ""

    # Imported lazily so missing lib doesn't break the whole backend
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except ImportError:
        log.warning("translate_ru_to_en: emergentintegrations not installed")
        return ""

    system_message = (
        "You are a professional menu translator. Translate the given Russian restaurant "
        "menu text into natural, concise English suitable for a tourist-friendly menu. "
        "Preserve proper nouns (dish names like 'Borscht', 'Pelmeni'), keep the tone neutral "
        "and appetizing. Do NOT add explanations, quotes, markdown, or punctuation that "
        "wasn't in the original. Return ONLY the translated text, nothing else."
    )

    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"menu-tr-{uuid.uuid4()}",
            system_message=system_message,
        ).with_model("gemini", "gemini-2.5-flash")

        resp = await chat.send_message(UserMessage(text=text.strip()))
        if not resp:
            return ""
        out = resp.strip().strip('"').strip("'")
        # Guard: if model echoed the prompt or returned something absurdly long,
        # still accept but cap length to 2× original as a sanity check.
        if len(out) > max(200, len(text) * 4):
            out = out[: max(200, len(text) * 4)]
        return out
    except Exception as e:  # noqa: BLE001 — resilient on purpose
        log.warning("translate_ru_to_en failed: %s", e)
        return ""
