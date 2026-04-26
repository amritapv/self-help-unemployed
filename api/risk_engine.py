"""
Module 02: AI Readiness & Displacement Risk
============================================
Takes Module 01's skills profile + frey_osborne + country config and returns
a calibrated automation risk struct, framed for non-technical readers.

Calibration: calibrated_score = raw_probability * country.infrastructure_factor

The output now produces a "verdict / what's changing / what stays / what to
learn" structure instead of leading with a percentage. Country-specific
language is injected via countries.json[CC].localization.

This module is deterministic — no LLM call. Templated phrasing is country
and region aware.
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

import anthropic

from api.platform_config import (
    isco_task_hints,
    is_supported_language,
    language_name as _language_name,
    verdict_bucket as _verdict_bucket,
)

_TRANSLATION_MODEL = "claude-sonnet-4-20250514"

# ISCO_TASK_HINTS now lives in data/isco_task_hints.json.
# Code that calls ISCO_TASK_HINTS.get(code) keeps working via this thin wrapper.
class _IscoTaskHintsView:
    def get(self, code, default=None):
        from api.platform_config import isco_task_hints as _h
        return _h(code) or default
    def __contains__(self, code):
        from api.platform_config import has_task_hints
        return has_task_hints(code)
    def __getitem__(self, code):
        from api.platform_config import isco_task_hints as _h
        v = _h(code)
        if v is None:
            raise KeyError(code)
        return v

ISCO_TASK_HINTS = _IscoTaskHintsView()


# NOTE: _verdict_bucket() is imported from api.platform_config at the top.
# Thresholds live in data/platform_config.json (verdict_thresholds.{mostly_safe_max, watch_max}).


def _verdict_label(bucket: str) -> str:
    return {
        "mostly_safe": "mostly safe",
        "watch": "worth watching",
        "act_now": "changing fast",
    }[bucket]


def _legacy_overall_risk(bucket: str) -> str:
    return {"mostly_safe": "low", "watch": "moderate", "act_now": "high"}[bucket]


def _region_horizon(country_config: dict[str, Any], region: str | None) -> int:
    """Pick urban or rural horizon from countries.json based on region.type."""
    loc = country_config.get("localization", {})
    default = loc.get("horizon_years_urban") or 10
    if not region:
        return default
    for r in country_config.get("regions", []):
        if r.get("code") == region:
            r_type = r.get("type", "")
            if "metro" in r_type or "industrial" in r_type or "ict" in r_type:
                return loc.get("horizon_years_urban", default)
            return loc.get("horizon_years_rural", default)
    return default


def _build_summary(
    occupation_title: str,
    country_name: str,
    bucket: str,
    horizon: int,
    loc: dict[str, Any],
) -> str:
    """One short paragraph — conversational, no percentages, no jargon."""
    label = _verdict_label(bucket)
    parts = [f"Look — what you do as a {occupation_title} here in {country_name}? It's {label}."]

    examples = loc.get("self_service_examples", [])
    if examples:
        parts.append(
            f"You've seen it before — {examples[0].lower()}. "
            "Same thing here: the boring stuff gets handed to machines, the clever stuff stays with you."
        )

    if bucket == "mostly_safe":
        parts.append(
            f"Over the next {horizon} years, machines might pick up a few of your simpler tasks, "
            "but most of your day still needs your eye and your people skills. You're alright."
        )
    elif bucket == "watch":
        parts.append(
            f"Over the next {horizon} years, a real chunk of what you do could shift to machines. "
            "Pick up one growing skill now and you'll stay ahead."
        )
    else:
        parts.append(
            f"Over the next {horizon} years, a lot of your work could shift to machines. "
            "Time to pivot — pick up something that still needs human judgement, before the squeeze hits harder."
        )

    return " ".join(parts)


def assess_automation_risk(
    skills_profile: dict[str, Any],
    country_config: dict[str, Any],
    frey_osborne: dict[str, Any],
    region: str | None = None,
    language: str = "en",
) -> dict[str, Any]:
    """Return automation risk struct keyed off the profile's primary matched ISCO.

    Args:
        skills_profile: Module 01 output dict; must have ``matched_occupations``
        country_config: countries.json[country_code] (should include localization)
        frey_osborne: full frey_osborne.json mapping ISCO -> {raw_probability, ...}
        region: optional region slug (e.g., "greater_accra"). Used to pick the
            urban-vs-rural horizon from country.localization.

    Returns:
        dict with these fields:
            verdict             — "mostly_safe" | "watch" | "act_now"
            verdict_label       — human-readable verdict ("mostly safe", ...)
            calibrated_score    — float 0..1
            horizon_years       — int
            summary_line        — single-sentence verdict
            plain_language_summary — full paragraph (verdict + context + horizon)
            machines_handling   — list of tasks machines are getting good at
            still_needs_you     — list of tasks that still need this person
            worth_learning      — list of country-localised growth pivots
            context_anchor      — local example reinforcing the framing
            # legacy fields for backward compatibility:
            overall_risk, at_risk_tasks, durable_skills, adjacent_skills_for_resilience
    """
    occupations = skills_profile.get("matched_occupations") or []
    country_name = country_config.get("country_name", "your country")
    loc = country_config.get("localization", {})

    if not occupations:
        return _maybe_translate(
            _empty_unknown_response("we couldn't identify a primary occupation from your background"),
            language,
        )

    primary = occupations[0]
    isco_code = str(primary.get("isco_code", "")).strip()
    occupation_title = primary.get("title", isco_code or "your work")

    fo_entry = frey_osborne.get(isco_code)
    factor = country_config.get("automation_calibration", {}).get("infrastructure_factor", 1.0)

    fallback_used: str | None = None
    if not fo_entry and isco_code:
        # Nearest-neighbour fallback: any ISCO in the same major group (first digit)
        # produces a usable estimate. Module 01 may surface a 4-digit code we
        # haven't curated yet (e.g. 7422 mobile repair vs our 7421 electronics).
        major = isco_code[0]
        candidates = [
            k for k in frey_osborne
            if not k.startswith("_") and k.startswith(major)
        ]
        if candidates:
            fallback_isco = min(candidates, key=lambda k: abs(int(k) - int(isco_code)))
            fo_entry = frey_osborne[fallback_isco]
            fallback_used = fallback_isco

    if not fo_entry:
        return _maybe_translate(
            _empty_unknown_response(
                f"we don't yet have automation-risk data for {occupation_title} (ISCO {isco_code}) in {country_name}",
                adjacent=loc.get("growth_pivots", []),
            ),
            language,
        )

    raw = float(fo_entry.get("raw_probability", 0.0))
    calibrated = round(raw * factor, 3)
    bucket = _verdict_bucket(calibrated)
    label = _verdict_label(bucket)
    horizon = _region_horizon(country_config, region)

    hint_isco = isco_code if isco_code in ISCO_TASK_HINTS else (fallback_used or isco_code)
    hints = ISCO_TASK_HINTS.get(hint_isco, {"machines_handle": [], "still_needs_you": []})

    growth_pivots = loc.get("growth_pivots", [])
    worth_learning = [p["skill"] for p in growth_pivots[:3] if "skill" in p]

    examples = loc.get("self_service_examples") or []
    context_anchor = examples[0] if examples else None

    summary = _build_summary(occupation_title, country_name, bucket, horizon, loc)
    if fallback_used:
        summary += (
            f" (Note: we don't yet have direct data for ISCO {isco_code}, so this estimate "
            f"is anchored on the closest occupation we have, ISCO {fallback_used}.)"
        )

    result = {
        "verdict": bucket,
        "verdict_label": label,
        "calibrated_score": calibrated,
        "horizon_years": horizon,
        "summary_line": f"What you do as a {occupation_title} here in {country_name}? It's {label}.",
        "plain_language_summary": summary,
        "machines_handling": hints["machines_handle"],
        "still_needs_you": hints["still_needs_you"],
        "worth_learning": worth_learning,
        "context_anchor": context_anchor,
        # Legacy compatibility — Module 03 + main.py still reference these.
        "overall_risk": _legacy_overall_risk(bucket),
        "at_risk_tasks": hints["machines_handle"],
        "durable_skills": hints["still_needs_you"],
        "adjacent_skills_for_resilience": worth_learning,
    }
    return _maybe_translate(result, language)


def _empty_unknown_response(reason: str, adjacent: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    adj_skills = [p["skill"] for p in (adjacent or [])[:3] if "skill" in p]
    return {
        "verdict": "unknown",
        "verdict_label": "not enough data",
        "calibrated_score": 0.0,
        "horizon_years": 0,
        "summary_line": "We can't yet estimate your automation risk.",
        "plain_language_summary": (
            f"{reason.capitalize()}. Tell us a bit more about your day-to-day work and we'll come back with an estimate."
        ),
        "machines_handling": [],
        "still_needs_you": [],
        "worth_learning": adj_skills,
        "context_anchor": None,
        "overall_risk": "unknown",
        "at_risk_tasks": [],
        "durable_skills": [],
        "adjacent_skills_for_resilience": adj_skills,
    }


# ── Translation pass ──────────────────────────────────────────────────────────

# Prose fields on the risk struct that are user-facing and must be translated.
_TRANSLATE_STRING_FIELDS = (
    "summary_line",
    "plain_language_summary",
    "verdict_label",
    "context_anchor",
)
_TRANSLATE_LIST_FIELDS = (
    "machines_handling",
    "still_needs_you",
    "worth_learning",
)


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text


def _maybe_translate(result: dict[str, Any], language: str) -> dict[str, Any]:
    """If language != 'en', call Sonnet to translate the prose fields.

    Translates: summary_line, plain_language_summary, verdict_label, context_anchor,
    machines_handling[], still_needs_you[], worth_learning[].

    Does NOT translate: numeric fields (calibrated_score, horizon_years), enum/tag
    fields (verdict, overall_risk). Legacy duplicate fields (at_risk_tasks,
    durable_skills, adjacent_skills_for_resilience) are kept in sync with their
    translated source lists.

    On failure: logs to stderr and returns the English version with
    `_translation_failed: true` added.
    """
    code = (language or "en").lower()
    if code == "en" or not is_supported_language(code):
        return result

    target_name = _language_name(code)

    # Build a payload of just the strings we need translated, keyed for round-trip.
    payload: dict[str, Any] = {}
    for f in _TRANSLATE_STRING_FIELDS:
        v = result.get(f)
        if isinstance(v, str) and v.strip():
            payload[f] = v
    for f in _TRANSLATE_LIST_FIELDS:
        v = result.get(f)
        if isinstance(v, list) and v:
            payload[f] = v

    if not payload:
        return result

    instruction = (
        f"Translate the following short labels and paragraph from English into {target_name}. "
        "Keep the meaning intact. Preserve any proper nouns (NVTI, PMKVY, ISCO codes, "
        "country names like Ghana, India). For Arabic, output in Arabic script with proper "
        "RTL-friendly punctuation. For Hindi, use Devanagari. Keep numbers and percentages "
        "in Western digits. Return ONLY a JSON object with the same keys and same list "
        "lengths/orderings as the input — no prose, no markdown fences. Each string field "
        "should map to a translated string; each list field should map to a list of "
        "translated strings of identical length."
    )

    user_message = (
        f"{instruction}\n\nINPUT JSON:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )

    try:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY not set")

        client = anthropic.Anthropic()
        response = client.messages.create(
            model=_TRANSLATION_MODEL,
            max_tokens=1500,
            system=(
                "You are a precise translator. You return ONLY a JSON object matching the "
                "shape of the input — no prose, no markdown fences, no commentary."
            ),
            messages=[{"role": "user", "content": user_message}],
        )
        text_block = next((b.text for b in response.content if b.type == "text"), "")
        raw = _strip_fences(text_block)
        translated = json.loads(raw)
        if not isinstance(translated, dict):
            raise ValueError("translation response was not a JSON object")

        out = dict(result)
        for f in _TRANSLATE_STRING_FIELDS:
            if f in payload and isinstance(translated.get(f), str):
                out[f] = translated[f]
        for f in _TRANSLATE_LIST_FIELDS:
            if f in payload and isinstance(translated.get(f), list):
                src_list = payload[f]
                new_list = translated[f]
                # Keep original length; if mismatched, pad/truncate to be safe.
                if len(new_list) != len(src_list):
                    if len(new_list) < len(src_list):
                        new_list = list(new_list) + src_list[len(new_list):]
                    else:
                        new_list = new_list[:len(src_list)]
                out[f] = [str(x) for x in new_list]

        # Keep legacy duplicate fields in sync with translated sources.
        if "machines_handling" in payload:
            out["at_risk_tasks"] = list(out["machines_handling"])
        if "still_needs_you" in payload:
            out["durable_skills"] = list(out["still_needs_you"])
        if "worth_learning" in payload:
            out["adjacent_skills_for_resilience"] = list(out["worth_learning"])

        return out
    except Exception as exc:  # noqa: BLE001
        print(
            f"[risk_engine] translation pass to {target_name} failed: {exc!r}",
            file=sys.stderr,
        )
        out = dict(result)
        out["_translation_failed"] = True
        return out
