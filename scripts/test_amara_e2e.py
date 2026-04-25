"""End-to-end test: Amara's chat input -> skills profile -> automation risk -> opportunities.

Calls the engine functions directly (skips FastAPI / Pydantic models in api/main.py
because those have schema mismatches with the engine outputs that need a separate
fix-up pass).

Usage:
  python scripts/test_amara_e2e.py            # full pipeline (needs ANTHROPIC_API_KEY, ~$0.10)
  python scripts/test_amara_e2e.py --dry-run  # skips Sonnet calls; prints filtered candidates only
  python scripts/test_amara_e2e.py --country IN
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api import opportunity_engine, risk_engine, skills_engine  # noqa: E402


# ── Personas ─────────────────────────────────────────────────────────────────

AMARA_GH = {
    "education": "I completed my WASSCE (secondary school) in 2019.",
    "experience": (
        "I've been running my own phone repair shop in Accra for about five years. "
        "I fix screens, replace batteries, diagnose circuit problems, and sometimes recover "
        "data from water-damaged phones. I taught two younger siblings the basics."
    ),
    "skills": (
        "Soldering, circuit diagnostics, screen replacement, basic Python from YouTube, "
        "customer service, teaching apprentices, cash handling."
    ),
    "additional_information": "I speak English fluently and Twi natively. I also know some Ga.",
    "country_code": "GH",
    "region": "greater_accra",
}

PRIYA_IN = {
    "education": "I finished Class 12 (HSC) last year.",
    "experience": (
        "I worked at my uncle's mobile repair shop on weekends for three years. "
        "I have been learning Python from YouTube tutorials and have built a small "
        "inventory tracking app for the shop."
    ),
    "skills": (
        "Mobile phone repair (screens, batteries), basic Python, troubleshooting, "
        "customer service, cash handling."
    ),
    "additional_information": "I speak Hindi natively, Kannada fluently, and English conversationally.",
    "country_code": "IN",
    "region": "karnataka",
}

PROFILES = {"GH": AMARA_GH, "IN": PRIYA_IN}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _hr(label: str) -> None:
    print()
    print("=" * 78)
    print(f"  {label}")
    print("=" * 78)


def _load_data() -> tuple[dict, dict]:
    countries = json.loads((ROOT / "data" / "countries.json").read_text(encoding="utf-8"))
    frey_osborne = json.loads((ROOT / "data" / "frey_osborne.json").read_text(encoding="utf-8"))
    return countries, frey_osborne


def _print_profile(profile: dict) -> None:
    print(profile.get("human_readable", "(no human-readable card)"))
    print()
    print("--- Structured (JSON) ---")
    public = {k: v for k, v in profile.items() if k != "human_readable"}
    print(json.dumps(public, indent=2)[:2500] + ("\n... [truncated]" if len(json.dumps(public)) > 2500 else ""))


def _print_risk(risk: dict) -> None:
    print(f"Overall risk:   {risk['overall_risk']} (calibrated {risk['calibrated_score']:.2f})")
    print()
    print(risk["plain_language_summary"])
    print()
    if risk["at_risk_tasks"]:
        print("At risk:")
        for t in risk["at_risk_tasks"]:
            print(f"  - {t}")
    if risk["durable_skills"]:
        print("Durable:")
        for t in risk["durable_skills"]:
            print(f"  - {t}")
    if risk["adjacent_skills_for_resilience"]:
        print("Adjacent skills to build:")
        for t in risk["adjacent_skills_for_resilience"]:
            print(f"  - {t}")


def _print_opportunities(opps: dict) -> None:
    if "raw_candidate_iscos" in opps:
        print(f"Candidate pool ({opps.get('candidates_considered', 0)}): {', '.join(opps['raw_candidate_iscos'])}")
        print()
    if not opps.get("opportunities"):
        print(f"No opportunities returned. Note: {opps.get('note', '(none)')}")
        return
    for i, opp in enumerate(opps["opportunities"], 1):
        print(f"[{i}] {opp['title']}  ({opp['opportunity_type']})")
        print(f"    Path:           {opp['employer_or_path']}")
        print(f"    Growth signal:  {opp['sector_growth_signal']}")
        print(f"    Wage:           {opp['wage_range']}")
        print(f"    Fit:            {opp['fit_explanation']}")
        if opp.get("skill_gap"):
            print(f"    Gap:            {opp['skill_gap']}")
        print(f"    Next step:      {opp['next_step']}")
        print()
    if opps.get("note"):
        print(f"Note: {opps['note']}")
    if opps.get("usage"):
        u = opps["usage"]
        print(f"Sonnet usage: input={u['input_tokens']} output={u['output_tokens']} cache_read={u['cache_read_input_tokens']} cache_write={u['cache_creation_input_tokens']}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--country", default="GH", choices=list(PROFILES.keys()))
    parser.add_argument("--dry-run", action="store_true", help="Skip both Sonnet calls; uses canned profile + filter only")
    args = parser.parse_args()

    persona = PROFILES[args.country]
    countries, frey_osborne = _load_data()

    if persona["country_code"] not in countries:
        print(f"!! No country config for {persona['country_code']}", file=sys.stderr)
        sys.exit(1)

    country_config = countries[persona["country_code"]]
    country_config["country_code"] = persona["country_code"]

    if args.dry_run:
        _hr("DRY RUN: synthetic Module 01 profile (no Sonnet call)")
        # Canned profile so we can test the filter + scoring without burning API.
        canned_profile = {
            "matched_occupations": [
                {"isco_code": "7421", "title": "Electronics Mechanics and Servicers", "confidence": "high"},
                {"isco_code": "2519", "title": "Software/Apps Developer (general)", "confidence": "medium"},
            ],
            "skills": [
                {"skill_name": "Repair electronic equipment", "skill_type": "skill/competence", "level": "advanced"},
                {"skill_name": "Use programming languages", "skill_type": "skill/competence", "level": "intermediate"},
            ],
            "languages": [
                {"language": "English", "proficiency": "fluent"},
                {"language": "Twi", "proficiency": "native"},
            ],
            "portable_summary": "You have hands-on technical skills in phone repair plus self-taught programming.",
        }
        _hr("Module 02: automation risk")
        risk = risk_engine.assess_automation_risk(canned_profile, country_config, frey_osborne)
        _print_risk(risk)

        _hr("Module 03: candidate filter (no Sonnet call)")
        candidates = opportunity_engine._build_candidates(canned_profile, country_config, frey_osborne)
        for c in candidates:
            tag = "M01-match" if c["is_module01_match"] else "lateral"
            print(
                f"  {c['isco_code']:<5} [{tag:<10}] risk={c['calibrated_risk']:<5.2f} "
                f"growth={(c['sector_growth_pct'] or 0)*100:>4.1f}% wages={c['wage_min']}-{c['wage_max']} {c['title']}"
            )
        return

    _hr("Module 01: skills assessment (Sonnet call)")
    profile = skills_engine.assess_skills(
        education=persona["education"],
        experience=persona["experience"],
        skills=persona["skills"],
        additional_information=persona["additional_information"],
        country_code=persona["country_code"],
        countries_config=countries,
    )
    _print_profile(profile)

    _hr("Module 02: automation risk (deterministic + template)")
    risk = risk_engine.assess_automation_risk(profile, country_config, frey_osborne)
    _print_risk(risk)

    _hr("Module 03: opportunity matching (Sonnet call)")
    opps = opportunity_engine.match_opportunities(
        skills_profile=profile,
        country_config=country_config,
        frey_osborne=frey_osborne,
        region=persona.get("region"),
    )
    _print_opportunities(opps)


if __name__ == "__main__":
    main()
