"""
Module 03: Opportunity Matching
================================
Two-stage:
  Stage A (deterministic) — for each ISCO with country wage_data, compute
    calibrated_risk + sector growth + Module-01 confidence + skill alignment.
    Filter: keep candidates that are EITHER in Module-01 matched_occupations
    OR share a major group with one of those matches. Cap at 8.
  Stage B (Sonnet) — single Sonnet call ranks the candidates and returns
    plain-language opportunities.

Output shape matches api/main.py Opportunity model:
  title, opportunity_type, employer_or_path, sector_growth_signal,
  wage_range, fit_explanation, skill_gap, next_step
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import anthropic
from dotenv import load_dotenv

from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

MODEL = "claude-sonnet-4-20250514"

_LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "es": "Spanish",
    "ar": "Arabic",
    "fr": "French",
}


def _language_name(code: str) -> str:
    """Map a language code to its English name. Falls back to English silently."""
    return _LANGUAGE_NAMES.get((code or "en").lower(), "English")

# Curated, demo-friendly titles for the ISCO codes we shipped first. Anything not
# in here falls back to the ESCO/ISCO taxonomy file so newly-onboarded countries
# get plain-English titles for free without a code change.
_CURATED_ISCO_TITLES: dict[str, str] = {
    "2512": "Software Developers",
    "2519": "Software and Applications Developers (general)",
    "3512": "ICT User Support Technicians",
    "3514": "Web Technicians",
    "4110": "General Office Clerks",
    "5223": "Shop Sales Assistants",
    "5311": "Childcare Workers",
    "6111": "Field Crop and Vegetable Growers",
    "7115": "Carpenters and Joiners",
    "7411": "Building and Related Electricians",
    "7412": "Electrical Mechanics and Fitters",
    "7421": "Electronics Mechanics and Servicers",
    "9211": "Crop Farm Labourers",
    "9520": "Street Vendors",
}


def _build_isco_titles() -> dict[str, str]:
    """Merge curated titles with whatever 4-digit codes the ISCO/ESCO taxonomy
    file provides. Curated entries win; taxonomy fills in the rest."""
    titles = dict(_CURATED_ISCO_TITLES)
    path = Path(__file__).resolve().parent.parent / "data" / "isco08_taxonomy.json"
    try:
        with open(path) as f:
            taxonomy = json.load(f)
    except Exception:
        return titles

    # Multiple ESCO entries can share a 4-digit ISCO code; pick the shortest
    # label as a rough proxy for "most general".
    fallback: dict[str, str] = {}
    for entry in taxonomy.values():
        code = str(entry.get("iscoCode", "")).strip()
        label = (entry.get("label") or "").strip()
        if len(code) != 4 or not label:
            continue
        if code not in fallback or len(label) < len(fallback[code]):
            fallback[code] = label

    for code, label in fallback.items():
        if code not in titles:
            titles[code] = label.title()
    return titles


ISCO_TITLES: dict[str, str] = _build_isco_titles()


def _confidence_value(c: Any) -> float:
    if isinstance(c, (int, float)):
        return float(c)
    return {"high": 0.9, "medium": 0.6, "low": 0.3}.get(str(c).lower(), 0.5)


def _major_group(isco_code: str) -> str:
    return isco_code[:1] if isco_code else ""


def _build_candidates(
    skills_profile: dict[str, Any],
    country_config: dict[str, Any],
    frey_osborne: dict[str, Any],
) -> list[dict[str, Any]]:
    matched = skills_profile.get("matched_occupations") or []
    matched_codes = {str(o.get("isco_code", "")).strip() for o in matched if o.get("isco_code")}
    matched_majors = {_major_group(c) for c in matched_codes if c}
    factor = country_config.get("automation_calibration", {}).get("infrastructure_factor", 1.0)

    wage_data = country_config.get("wage_data", {})
    sectors = country_config.get("sectors", {})

    # Build candidates for every wage_data ISCO, tagging by relationship to M01.
    # Sonnet picks the top 5 from the scored pool — broad laterals are kept so
    # we can always honour "top 5" even when M01 surfaces only one occupation.
    candidates: list[dict[str, Any]] = []
    for isco, wage in wage_data.items():
        if isco.startswith("_"):
            continue

        is_module01_match = isco in matched_codes
        is_same_major = _major_group(isco) in matched_majors and not is_module01_match
        # source tag: "m01_match" | "same_major_lateral" | "broad_lateral"
        if is_module01_match:
            source = "m01_match"
        elif is_same_major:
            source = "same_major_lateral"
        else:
            source = "broad_lateral"

        fo = frey_osborne.get(isco, {})
        raw = float(fo.get("raw_probability", 0.0))
        calibrated = round(raw * factor, 3)
        sector_slug = wage.get("sector")
        sector_data = sectors.get(sector_slug, {})

        confidence = next(
            (_confidence_value(o.get("confidence")) for o in matched if str(o.get("isco_code", "")).strip() == isco),
            0.0,
        )

        candidates.append({
            "isco_code": isco,
            "title": ISCO_TITLES.get(isco, isco),
            "sector": sector_slug,
            "sector_growth_pct": sector_data.get("growth_annual"),
            "informality_share": sector_data.get("informal_share"),
            "wage_min": wage.get("min"),
            "wage_max": wage.get("max"),
            "wage_median": wage.get("median"),
            "currency_code": country_config["currency"]["code"],
            "currency_symbol": country_config["currency"]["symbol"],
            "raw_risk": raw,
            "calibrated_risk": calibrated,
            "task_breakdown": fo.get("task_breakdown", {}),
            "is_module01_match": is_module01_match,
            "is_same_major_lateral": is_same_major,
            "source": source,
            "module01_confidence": confidence,
            "training_pathways": [
                tp for tp in country_config.get("training_pathways", [])
                if isco in tp.get("leads_to_isco", [])
            ],
        })

    # Score: prioritise M01 matches, then same-major laterals, then broad
    # laterals. Within each tier, prefer low automation risk + high sector growth.
    source_priority = {"m01_match": 2, "same_major_lateral": 1, "broad_lateral": 0}
    candidates.sort(
        key=lambda c: (
            source_priority[c["source"]],
            -c["calibrated_risk"],
            c.get("sector_growth_pct") or 0.0,
        ),
        reverse=True,
    )
    return candidates[:8]


def _format_candidate(c: dict[str, Any]) -> str:
    pathways = "; ".join(
        f"{tp['id']} ({tp['name']}, {tp['duration_weeks']}wk, cost {c['currency_code']} {tp['cost_local']})"
        for tp in c["training_pathways"]
    ) or "none configured"
    sector_growth = f"{(c['sector_growth_pct'] or 0)*100:.1f}%/yr" if c.get("sector_growth_pct") is not None else "n/a"
    tb = c.get("task_breakdown") or {}
    source_label = {
        "m01_match": "Module 01 match (the user's primary occupation)",
        "same_major_lateral": "lateral pivot, same ISCO major group",
        "broad_lateral": "broad lateral — different field, surfaced as a stretch option",
    }[c["source"]]
    return (
        f"--- ISCO {c['isco_code']}: {c['title']} ---\n"
        f"- Source: {source_label}\n"
        f"- Sector: {c.get('sector','n/a')} (growth {sector_growth}, informal share {(c.get('informality_share') or 0)*100:.0f}%)\n"
        f"- Wage band ({c['currency_code']}/mo): min {c['wage_min']}, max {c['wage_max']}, median {c['wage_median']}\n"
        f"- Calibrated automation risk: {c['calibrated_risk']:.2f} (raw F-O {c['raw_risk']:.2f} × country factor)\n"
        f"  Task mix: routine {(tb.get('routine_share') or 0)*100:.0f}%, "
        f"creative {(tb.get('creative_share') or 0)*100:.0f}%, "
        f"social {(tb.get('social_share') or 0)*100:.0f}%\n"
        f"- Training pathways for this ISCO: {pathways}"
    )


def _build_prompt(
    skills_profile: dict[str, Any],
    country_config: dict[str, Any],
    candidates: list[dict[str, Any]],
    region: str | None,
    language: str = "en",
) -> tuple[str, str]:
    cur = country_config["currency"]
    sector_lines = [
        f"  - {name}: growth {s['growth_annual']*100:.1f}%/yr, employs {s['share_employment']*100:.0f}% of workers, informal share {s['informal_share']*100:.0f}%"
        for name, s in country_config["sectors"].items()
    ]
    pathway_lines = [
        f"  - {tp['id']}: {tp['name']} ({tp['duration_weeks']}wk, cost {cur['code']} {tp['cost_local']}, leads to ISCO {','.join(tp['leads_to_isco'])})"
        for tp in country_config.get("training_pathways", [])
    ]

    system = f"""You are UNMAPPED's opportunity matcher. You produce 3-5 honest, realistic job recommendations for a young person in a low- or middle-income country.

# Country context: {country_config['country_name']} ({country_config['country_code']})
- Currency: {cur['symbol']} ({cur['code']}) per month
- Languages: primary {country_config['language']['primary']}; local {', '.join(country_config['language'].get('local', []))}
- Youth unemployment: {country_config['demographics']['youth_unemployment_rate']*100:.1f}% | informality: {country_config['demographics']['informality_rate']*100:.0f}%
- Automation calibration: country infrastructure_factor = {country_config['automation_calibration']['infrastructure_factor']} ({country_config['automation_calibration']['rationale']}). Calibrated_risk in the candidates below is already country-adjusted.

## Sectors
{chr(10).join(sector_lines)}

## Training pathways available in {country_config['country_name']}
{chr(10).join(pathway_lines) if pathway_lines else '(none configured)'}

# How you work
1. Rank candidates by realistic fit (skill alignment + automation resilience + reachability).
2. Pick exactly the TOP 5 opportunities. Order best first. Always return 5 unless the candidate pool is smaller, in which case return them all.
3. CITE numbers verbatim from the candidates list — don't invent wages, growth rates, or pathways.
4. Use ONLY ISCO codes from the candidates list. Use ONLY training_pathway IDs from the country pathways.
5. WRITE LIKE A FRIEND, NOT A RECRUITER. Use contractions ("you'd", "you're", "you've"). Use everyday phrasing — talk like a mentor over tea, not a corporate brochure. Avoid these dead words: "demonstrate", "leverage", "utilize/utilise", "translates well to", "transferable skills", "robust", "synergies", "competencies", "qualifications". Wrap numbers in meaning ("Construction has grown 7% per year recently") — never raw jargon.
6. Be honest about gaps. If a match needs certification, say which pathway from the list — in plain words ("you'll need to grab the NVTI cert — it's 12 weeks").
7. If the user's seeded skills are too thin, return an empty `opportunities` list and put a sentence explaining in `note`.

# Output
Return JSON with this exact shape — nothing else, no markdown fences:
{{
  "opportunities": [
    {{
      "title": "Plain-language role title (e.g., 'Mobile Device Technician')",
      "opportunity_type": "formal_employment | self_employment | gig | apprenticeship | training_pathway",
      "employer_or_path": "An employer name OR the path (e.g., 'Self-employment in your neighbourhood')",
      "wage_range": "Wage as a range with the floor (minimum) on the low end and the high end clearly framed. Cite the candidate's wage_min and wage_max verbatim. Format: '<currency> <floor> (starting) – <high> (high end) /month'. Example: 'GHS 1,800 (starting) – 2,400 (high end) /month'. Always show both ends.",
      "sector_growth": "Friendly, non-technical description of how this job's sector is growing — for someone with no business or economics vocabulary. NO jargon (avoid words like 'ICT', 'CAGR', 'sector growth rate'). Translate sector slugs to everyday words: 'ict' -> 'tech and digital jobs', 'renewable_energy' -> 'solar and renewable energy', 'services' -> 'services and repair work', 'manufacturing' -> 'factory and manufacturing work', 'agriculture' -> 'farming', 'construction' -> 'building and construction', 'retail' -> 'shops and selling', 'finance' -> 'banking', 'healthcare' -> 'health and care work', 'education' -> 'teaching'. Cite the candidate's sector_growth_pct number verbatim. Example: 'Tech and digital jobs are growing fast — about 14% more work each year.' or 'Mobile repair and services have steady demand, with about 6% more work each year.'",
      "fit_explanation": "ONE short, conversational sentence (15-25 words). Talk like a friend giving honest advice. Use contractions and everyday words. Cite the user's actual skills naturally. Examples of the right tone: 'Your phone-repair chops carry straight over here — you already know what most of the day looks like.' or 'You're not far off — the soldering and circuit work map nicely, you'd just need to learn solar wiring.' AVOID: 'Your skills translate well to', 'demonstrates strong alignment', 'leverages your background'.",
      "skill_gap": "What the user is missing (or null if no gap). Casual phrasing — 'You'll need a solar cert' not 'Lacks certification in photovoltaic systems'.",
      "next_step": "One concrete action, casual and direct — 'Sign up for the free Energy Commission solar course (it's 2 weeks)' or 'Walk into the NVTI office and ask about the Q3 intake'. Must reference a pathway ID by name when applicable."
    }}
  ],
  "note": "Optional explanation if you returned <3 opportunities or no opportunities"
}}

# LANGUAGE
Respond in {_language_name(language)}. Specifically:
- title, employer_or_path, wage_range, sector_growth, fit_explanation, skill_gap, next_step, note: write in {_language_name(language)}.
- opportunity_type: keep as one of the English enum values exactly: formal_employment | self_employment | gig | apprenticeship | training_pathway.
- isco_code values, training_pathway IDs (e.g., nvti_solar_2wk), and currency codes (e.g., GHS, INR) referenced inline: keep verbatim — they are identifiers.
- Numeric values cited from the candidates list (wages, growth percentages): keep verbatim."""

    summary = skills_profile.get("portable_summary", "")
    occupations_text = "\n".join(
        f"  - {o.get('isco_code')}: {o.get('title')} (confidence: {o.get('confidence')})"
        for o in (skills_profile.get("matched_occupations") or [])
    ) or "  (none surfaced by Module 01)"
    skills_text = "\n".join(
        f"  - [{s.get('level','?')}] {s.get('skill_name','?')} — {s.get('skill_type','?')}"
        for s in (skills_profile.get("skills") or [])[:15]
    ) or "  (none extracted)"
    languages_text = ", ".join(
        f"{lg.get('language')} ({lg.get('proficiency')})"
        for lg in (skills_profile.get("languages") or [])
    ) or "(none provided)"

    candidates_text = "\n\n".join(_format_candidate(c) for c in candidates)

    user = f"""# User profile (Module 01 output)

Portable summary: {summary or '(none)'}

Matched occupations (ISCO):
{occupations_text}

Top skills:
{skills_text}

Languages: {languages_text}
Region of interest: {region or 'any region'}

# Candidate occupations (pre-filtered)

{candidates_text}

Return JSON per the schema. Pick the TOP 5 best matches in fit-order. If the candidate pool is smaller than 5, return them all. If nothing fits well, return empty opportunities and put the reason in `note`."""

    return system, user


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text


def match_opportunities(
    skills_profile: dict[str, Any],
    country_config: dict[str, Any],
    frey_osborne: dict[str, Any],
    region: str | None = None,
    language: str = "en",
) -> dict[str, Any]:
    """Run Stage A filter + Stage B Sonnet ranking.

    Returns dict with keys ``opportunities`` (list[dict]) and ``note`` (str|None).
    Each opportunity dict matches api/main.py Opportunity model.
    """
    candidates = _build_candidates(skills_profile, country_config, frey_osborne)

    if not candidates:
        return {
            "opportunities": [],
            "note": (
                "No candidate occupations passed the filter — Module 01 didn't surface any ISCO "
                "we have country wage data for, and no lateral pivots were available."
            ),
            "candidates_considered": 0,
        }

    system, user = _build_prompt(skills_profile, country_config, candidates, region, language)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY not set. Copy .env.example to .env and fill it in.")

    client = anthropic.Anthropic()
    # Note: model is claude-sonnet-4-20250514 (Sonnet 4). It does NOT support
    # `thinking: adaptive` or `output_config.effort` — those are 4.6+ only.
    # If the model is bumped to claude-sonnet-4-6 or later, re-add:
    #   thinking={"type": "adaptive"}, output_config={"effort": "medium"}
    response = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )

    text_block = next((b.text for b in response.content if b.type == "text"), "")
    raw = _strip_fences(text_block)
    if not raw:
        block_types = [b.type for b in response.content]
        raise ValueError(
            f"Sonnet returned no text block. stop_reason={response.stop_reason}; blocks={block_types}; "
            f"usage={response.usage}"
        )
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Sonnet returned non-JSON:\n{raw}") from exc

    parsed["candidates_considered"] = len(candidates)
    parsed["raw_candidate_iscos"] = [c["isco_code"] for c in candidates]
    parsed["usage"] = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cache_read_input_tokens": getattr(response.usage, "cache_read_input_tokens", 0),
        "cache_creation_input_tokens": getattr(response.usage, "cache_creation_input_tokens", 0),
    }
    return parsed
