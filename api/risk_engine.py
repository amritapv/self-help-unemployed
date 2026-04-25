"""
Module 02: AI Readiness & Displacement Risk
============================================
Takes Module 01's skills profile + frey_osborne + country config and returns
a calibrated automation risk struct with plain-language phrasing.

Calibration: calibrated_score = raw_probability * country.infrastructure_factor

This module is deliberately deterministic (no LLM call for the numeric path).
Plain-language phrasing is templated. If the team wants Sonnet-generated copy
later, swap _phrasing() for an LLM call.
"""

from __future__ import annotations

from typing import Any

ISCO_TASK_HINTS: dict[str, dict[str, list[str]]] = {
    "7421": {
        "at_risk": ["Routine diagnostic checks", "Standard screen replacements"],
        "durable": ["Complex circuit repair", "Customer problem diagnosis", "Teaching apprentices"],
    },
    "2519": {
        "at_risk": ["Boilerplate code generation", "Routine bug fixing on well-known stacks"],
        "durable": ["System design", "Translating user needs into software", "Self-directed learning of new tools"],
    },
    "3512": {
        "at_risk": ["Password resets", "Tier-1 ticket triage"],
        "durable": ["Hands-on hardware troubleshooting", "Onsite user training", "Multi-language user support"],
    },
    "5223": {
        "at_risk": ["Cashier-style checkout", "Inventory counting"],
        "durable": ["Persuasive selling", "Building customer relationships", "In-store troubleshooting"],
    },
    "7411": {
        "at_risk": ["Routine wiring inspections"],
        "durable": ["Solar PV installation", "On-site fault diagnosis", "Code-compliance work"],
    },
}


def _level(score: float) -> str:
    if score < 0.33:
        return "low"
    if score < 0.66:
        return "moderate"
    return "high"


def _phrasing(score: float, country_name: str, occupation_title: str) -> str:
    pct = round(score * 100)
    bucket = _level(score)
    if bucket == "low":
        return (
            f"Your work as a {occupation_title} has low automation risk in {country_name}. "
            f"About {pct} out of every 100 tasks in this kind of work could be done by machines, "
            "but most of what you do depends on judgement that's hard to replace."
        )
    if bucket == "moderate":
        return (
            f"Your work as a {occupation_title} has moderate automation risk in {country_name}. "
            f"About {pct} out of every 100 tasks in this kind of work could be done by machines in time. "
            "Building adjacent skills now puts you ahead."
        )
    return (
        f"Your work as a {occupation_title} has high automation risk in {country_name} over the long run. "
        f"About {pct} out of every 100 tasks in this kind of work could be automated, "
        "so a pivot to skills with stronger human judgement will protect you."
    )


def _adjacent_skills(isco_code: str) -> list[str]:
    """Hand-curated upskilling suggestions per ISCO. Keep short — the demo
    surfaces these as bullets, not paragraphs."""
    suggestions = {
        "7421": [
            "Solar panel installation & maintenance",
            "Data recovery & software troubleshooting",
            "Basic networking / Wi-Fi setup",
        ],
        "2519": [
            "Mobile-first development",
            "Working with AI APIs",
            "Database design and SQL",
        ],
        "3512": [
            "Cybersecurity fundamentals",
            "Cloud admin (basic AWS or Azure)",
            "Network troubleshooting",
        ],
        "5223": [
            "Digital marketing for small businesses",
            "Inventory and POS software",
            "Customer relationship management",
        ],
        "7411": [
            "Solar PV systems",
            "Smart-home wiring",
            "Building energy efficiency basics",
        ],
    }
    return suggestions.get(
        isco_code,
        [
            "Hands-on technical skills with growing demand in your country",
            "Customer-facing skills that machines cannot easily replace",
            "Adjacent specialisations in your field",
        ],
    )


def assess_automation_risk(
    skills_profile: dict[str, Any],
    country_config: dict[str, Any],
    frey_osborne: dict[str, Any],
) -> dict[str, Any]:
    """Return automation risk struct keyed off the profile's primary matched ISCO.

    Args:
        skills_profile: Module 01 output dict; must have ``matched_occupations``
        country_config: countries.json[country_code]
        frey_osborne: full frey_osborne.json mapping ISCO -> {raw_probability, ...}

    Returns:
        dict matching api/main.py AutomationRisk schema fields:
        ``overall_risk``, ``calibrated_score``, ``at_risk_tasks``,
        ``durable_skills``, ``adjacent_skills_for_resilience``,
        ``plain_language_summary``.
    """
    occupations = skills_profile.get("matched_occupations") or []
    if not occupations:
        return {
            "overall_risk": "unknown",
            "calibrated_score": 0.0,
            "at_risk_tasks": [],
            "durable_skills": [],
            "adjacent_skills_for_resilience": [],
            "plain_language_summary": (
                "We couldn't identify a primary occupation from your background, "
                "so we can't yet estimate automation risk. Tell us a bit more about your day-to-day work."
            ),
        }

    primary = occupations[0]
    isco_code = str(primary.get("isco_code", "")).strip()
    occupation_title = primary.get("title", isco_code or "your work")

    fo_entry = frey_osborne.get(isco_code)
    factor = country_config.get("automation_calibration", {}).get("infrastructure_factor", 1.0)
    country_name = country_config.get("country_name", "your country")

    fallback_used: str | None = None
    if not fo_entry and isco_code:
        # Nearest-neighbour fallback: any ISCO in the same major group (first digit)
        # produces a usable estimate. Module 01 may surface a 4-digit code we
        # haven't curated yet (e.g. 7422 mobile repair vs our 7421 electronics).
        major = isco_code[0]
        candidates = [k for k, v in frey_osborne.items() if not k.startswith("_") and k.startswith(major)]
        if candidates:
            fallback_isco = min(candidates, key=lambda k: abs(int(k) - int(isco_code)))
            fo_entry = frey_osborne[fallback_isco]
            fallback_used = fallback_isco

    if not fo_entry:
        return {
            "overall_risk": "unknown",
            "calibrated_score": 0.0,
            "at_risk_tasks": [],
            "durable_skills": [],
            "adjacent_skills_for_resilience": _adjacent_skills(isco_code),
            "plain_language_summary": (
                f"We don't yet have automation-risk data for {occupation_title} (ISCO {isco_code}) in {country_name}. "
                "We'll fill this in as more occupational data lands."
            ),
        }

    raw = float(fo_entry.get("raw_probability", 0.0))
    calibrated = round(raw * factor, 3)
    hint_isco = isco_code if isco_code in ISCO_TASK_HINTS else (fallback_used or isco_code)
    hints = ISCO_TASK_HINTS.get(hint_isco, {"at_risk": [], "durable": []})
    summary = _phrasing(calibrated, country_name, occupation_title)
    if fallback_used:
        summary += (
            f" (Note: we don't yet have direct data for ISCO {isco_code}, so this estimate "
            f"is anchored on the closest occupation we have, ISCO {fallback_used}.)"
        )

    return {
        "overall_risk": _level(calibrated),
        "calibrated_score": calibrated,
        "at_risk_tasks": hints["at_risk"],
        "durable_skills": hints["durable"],
        "adjacent_skills_for_resilience": _adjacent_skills(hint_isco),
        "plain_language_summary": summary,
    }
