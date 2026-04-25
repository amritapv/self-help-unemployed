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

ISCO_TITLES: dict[str, str] = {
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

    candidates: list[dict[str, Any]] = []
    for isco, wage in wage_data.items():
        if isco.startswith("_"):
            continue

        is_module01_match = isco in matched_codes
        is_lateral = _major_group(isco) in matched_majors and not is_module01_match
        if not (is_module01_match or is_lateral):
            continue

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
            "module01_confidence": confidence,
            "training_pathways": [
                tp for tp in country_config.get("training_pathways", [])
                if isco in tp.get("leads_to_isco", [])
            ],
        })

    candidates.sort(
        key=lambda c: (
            c["is_module01_match"],
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
    return (
        f"--- ISCO {c['isco_code']}: {c['title']} ---\n"
        f"- Source: {'Module 01 match' if c['is_module01_match'] else 'lateral pivot (same major group)'}\n"
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
2. Pick 3-5 opportunities. Order best first.
3. CITE numbers verbatim from the candidates list — don't invent wages, growth rates, or pathways.
4. Use ONLY ISCO codes from the candidates list. Use ONLY training_pathway IDs from the country pathways.
5. Plain language. Wrap numbers in meaning ("Construction has grown 7% per year recently") — never raw jargon.
6. Be honest about gaps. If a match needs certification, say which pathway from the list.
7. If the user's seeded skills are too thin, return an empty `opportunities` list and put a sentence explaining in `note`.

# Output
Return JSON with this exact shape — nothing else, no markdown fences:
{{
  "opportunities": [
    {{
      "title": "Plain-language role title (e.g., 'Mobile Device Technician')",
      "opportunity_type": "formal_employment | self_employment | gig | apprenticeship | training_pathway",
      "employer_or_path": "An employer name OR the path (e.g., 'Self-employment in your neighbourhood')",
      "sector_growth_signal": "Plain-language sentence with the sector growth number cited verbatim",
      "wage_range": "Plain-language wage band, e.g., 'Expected earnings: GHS 1,800 – 2,400 per month'",
      "fit_explanation": "1-2 sentences citing the user's actual skills",
      "skill_gap": "What the user is missing (or null if no gap)",
      "next_step": "One concrete action — e.g., 'Register at NVTI for the next intake' (must reference a pathway ID if applicable)"
    }}
  ],
  "note": "Optional explanation if you returned <3 opportunities or no opportunities"
}}"""

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

Return JSON per the schema. Pick 3-5 best matches in fit-order. If nothing fits well, return empty opportunities and put the reason in `note`."""

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

    system, user = _build_prompt(skills_profile, country_config, candidates, region)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY not set. Copy .env.example to .env and fill it in.")

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        thinking={"type": "adaptive"},
        output_config={"effort": "medium"},
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
