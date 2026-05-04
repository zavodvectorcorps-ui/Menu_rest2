"""Lightweight RU→EN translation for menu content.

Uses Gemini flash via emergentintegrations.
- `translate_ru_to_en(text)` — fail-silent, returns "" so the caller can fall back to RU.
- `translate_ru_to_en_strict(text)` — raises on errors so endpoints can surface the real cause.
"""
import os
import logging
import uuid

log = logging.getLogger(__name__)


async def _do_translate(text: str, max_retries: int = 3) -> str:
    """Inner implementation — raises on errors. Returns translated text.
    Retries up to `max_retries` times on transient errors / empty responses."""
    if not text or not text.strip():
        return ""

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

    import asyncio
    last_err = None
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
        # Brief backoff before retry
        if attempt < max_retries - 1:
            await asyncio.sleep(0.5 * (attempt + 1))

    raise last_err or RuntimeError("LLM translation failed after retries")


async def translate_ru_to_en(text: str) -> str:
    """Fail-silent variant for background tasks: returns "" on error."""
    try:
        return await _do_translate(text)
    except Exception as e:
        log.warning("translate_ru_to_en failed: %s", e)
        return ""


async def translate_ru_to_en_strict(text: str) -> str:
    """Strict variant: raises on error. Use in pre-flight checks where the
    caller wants to report the real cause to the user."""
    return await _do_translate(text)
