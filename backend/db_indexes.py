"""Idempotent index creation. Runs on backend startup.

Adding indexes is safe — Mongo's create_index is a no-op if an index with
the same key/options already exists. We focus on hot paths: any query that
filters by `restaurant_id`, lookups by `slug`/`code`, and time-range scans
on `created_at` for analytics.

If a single index call fails (e.g. permissions), we log and continue —
missing indexes degrade performance but do not break correctness.
"""
import logging
from database import db

log = logging.getLogger(__name__)


# (collection_name, [(field, direction), ...], options_dict)
INDEXES: list[tuple[str, list, dict]] = [
    # Lookups by slug / code (1-row fetches, but used on every menu render)
    ("restaurants", [("slug", 1)], {"sparse": True}),
    ("tables", [("code", 1)], {}),
    # All hot per-tenant queries
    ("tables", [("restaurant_id", 1)], {}),
    ("menu_sections", [("restaurant_id", 1)], {}),
    ("categories", [("restaurant_id", 1), ("sort_order", 1)], {}),
    ("menu_items", [("restaurant_id", 1), ("sort_order", 1)], {}),
    ("labels", [("restaurant_id", 1)], {}),
    ("splash_ads", [("restaurant_id", 1), ("is_active", 1)], {}),
    ("call_types", [("restaurant_id", 1), ("sort_order", 1)], {}),
    ("settings", [("restaurant_id", 1)], {}),
    # Analytics / write-heavy collections (also growing fast)
    ("menu_views", [("restaurant_id", 1), ("created_at", -1)], {}),
    ("orders", [("restaurant_id", 1), ("created_at", -1)], {}),
    ("orders", [("restaurant_id", 1), ("status", 1)], {}),
    ("staff_calls", [("restaurant_id", 1), ("created_at", -1)], {}),
    ("staff_calls", [("restaurant_id", 1), ("status", 1)], {}),
    # Auth
    ("users", [("username", 1)], {"unique": True}),
    # Translation cache (already created in services/translation.py, but safe to re-declare)
    ("translation_cache", [("key_ru", 1)], {"unique": True}),
]


async def ensure_indexes() -> None:
    """Create indexes idempotently. Background = True so the call returns
    quickly even on collections that have grown large."""
    created = 0
    for collection_name, keys, opts in INDEXES:
        try:
            # background=True lets Mongo build the index without blocking writes
            await db[collection_name].create_index(keys, background=True, **opts)
            created += 1
        except Exception as e:
            log.warning("Failed to create index on %s %s: %s", collection_name, keys, e)
    log.info("ensure_indexes: %d/%d indexes ensured", created, len(INDEXES))
