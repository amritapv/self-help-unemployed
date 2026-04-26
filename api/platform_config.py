"""Platform-wide config loader.

Single source of truth for things that are NOT country-specific:
  - language code -> human name + native name + RTL flag
  - automation-risk verdict thresholds
  - sector slug -> friendly English noun phrase
  - opportunity_type metadata

Reads `data/platform_config.json` once and caches. Every engine should
go through these helpers instead of holding its own private dict — that's
how the spec's "configurable without changing your codebase" guarantee
holds for languages, sectors, and verdict tuning.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "data" / "platform_config.json"
_TASK_HINTS_PATH = Path(__file__).resolve().parent.parent / "data" / "isco_task_hints.json"


@lru_cache(maxsize=1)
def _config() -> dict[str, Any]:
    with open(_CONFIG_PATH, encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def _task_hints() -> dict[str, Any]:
    with open(_TASK_HINTS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


# ── Language helpers ─────────────────────────────────────────────────────────


def language_name(code: str) -> str:
    """Map a language code to its English name. Falls back to English silently."""
    code = (code or "en").lower()
    entry = _config().get("languages", {}).get(code)
    if not entry:
        return "English"
    return entry.get("name", "English")


def is_supported_language(code: str) -> bool:
    return (code or "").lower() in _config().get("languages", {})


def all_language_codes() -> list[str]:
    return [c for c in _config().get("languages", {}) if not c.startswith("_")]


# ── Verdict thresholds (Module 02) ───────────────────────────────────────────


def verdict_bucket(score: float) -> str:
    """Map a calibrated automation-risk score to one of three verdict tags.

    Thresholds live in platform_config.json so retuning them is JSON-only.
    """
    th = _config().get("verdict_thresholds", {})
    mostly_safe_max = float(th.get("mostly_safe_max", 0.33))
    watch_max = float(th.get("watch_max", 0.66))
    if score < mostly_safe_max:
        return "mostly_safe"
    if score < watch_max:
        return "watch"
    return "act_now"


# ── Sector translations (Module 03) ──────────────────────────────────────────


def sector_translations(language: str = "en") -> dict[str, str]:
    """English noun phrases per sector slug. For non-English languages we
    return the English mapping anyway — the matcher prompt's per-language
    instruction handles translation downstream."""
    table = _config().get("sector_translations", {})
    return table.get((language or "en").lower(), table.get("en", {}))


# ── Opportunity-type metadata (Module 03) ────────────────────────────────────


def opportunity_type_metadata() -> dict[str, dict[str, Any]]:
    """Every type the platform recognises. Per-country availability is in
    countries.<CC>.opportunity_types — that list is what's piped into the
    matcher prompt at request time."""
    raw = _config().get("opportunity_type_metadata", {})
    return {k: v for k, v in raw.items() if not k.startswith("_")}


# ── ISCO task hints (Module 02) ──────────────────────────────────────────────


def isco_task_hints(isco_code: str) -> dict[str, list[str]] | None:
    """Return the {machines_handle: [...], still_needs_you: [...]} entry for
    a 4-digit ISCO code, or None if we don't have hints yet."""
    if not isco_code:
        return None
    return _task_hints().get(str(isco_code).strip())


def has_task_hints(isco_code: str) -> bool:
    return isco_task_hints(isco_code) is not None
