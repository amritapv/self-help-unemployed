"""
Seed the policymaker aggregation DB with synthetic profiles.

Plausible distributions sampled from countries.json priors (sector employment
shares, regions, ISCO wage_data) and frey_osborne.json (automation probs).
Skills come from esco_skills.json — keyword-matched per ISCO major group so
the resulting `top_skills` aggregation uses real ESCO labels and URIs.

Opportunities are minted via opportunity_engine._build_candidates — no Claude
calls, free to run.

Usage:
  python scripts/seed_synthetic.py                # 300 per country, replace synthetic
  python scripts/seed_synthetic.py --per-country 500
  python scripts/seed_synthetic.py --countries GH
  python scripts/seed_synthetic.py --no-reset     # append rather than replace
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api import repository  # noqa: E402
from api.db import init_db  # noqa: E402
from api.gap_taxonomy import CANONICAL_GAPS  # noqa: E402
from api.opportunity_engine import ISCO_TITLES, _build_candidates  # noqa: E402


DATA_DIR = ROOT / "data"


# ── ESCO skill pools, themed by ISCO major group via keyword match ────────────

# Keys are ISCO-08 major group digits (first char of the 4-digit code).
# Each list is keyword anchors — any ESCO skill whose label contains one of
# these (case-insensitive) is eligible for that major group's pool.
KEYWORDS_BY_MAJOR_GROUP: dict[str, list[str]] = {
    "2": [  # Professionals — ICT-leaning given our wage_data
        "program", "software", "database", "sql", "web develop",
        "javascript", "python", "html", "css", "version control",
    ],
    "3": [  # Technicians (ICT support, web tech, electrical/electronic)
        "technician", "ict support", "computer hardware", "network",
        "install software", "diagnose", "troubleshoot", "user support",
    ],
    "4": [  # Clerical
        "office administration", "data entry", "filing", "clerical",
        "spreadsheet", "office software", "record",
    ],
    "5": [  # Services / sales / care
        "customer service", "sales technique", "retail", "cash handling",
        "childcare", "child care", "hospitality", "interact with customers",
    ],
    "6": [  # Agriculture
        "crop", "soil", "irrigation", "livestock", "harvest", "plant",
        "fertiliz",
    ],
    "7": [  # Crafts / trades
        "carpentry", "electric", "wiring", "weld", "solar", "plumb",
        "electronics", "repair", "construction", "install electrical",
    ],
    "9": [  # Elementary
        "clean", "manual", "warehouse", "load", "stock", "delivery",
    ],
}

# Cross-cutting skills every profile pulls 1-2 from
GENERIC_KEYWORDS = [
    "communicat", "teamwork", "time management", "problem solv",
    "literacy", "numeracy", "leadership",
]

POOL_CAP_PER_GROUP = 18  # cap themed pool size so aggregation has visible peaks
GENERIC_POOL_CAP = 10

LEVELS = ["basic", "intermediate", "advanced"]
LEVEL_WEIGHTS = [0.5, 0.35, 0.15]

EDUCATION_DISTRIBUTION = [
    ("ISCED_2", "Lower secondary", 0.32),
    ("ISCED_3", "Upper secondary", 0.42),
    ("ISCED_4", "Post-secondary non-tertiary", 0.10),
    ("ISCED_5", "Short-cycle tertiary", 0.10),
    ("ISCED_6", "Bachelor's or equivalent", 0.06),
]

OPPORTUNITY_TYPES = [
    "formal_employment",
    "self_employment",
    "gig",
    "apprenticeship",
    "training_pathway",
]

# Synthetic gaps draw from the same canonical taxonomy used for live writes,
# minus "Other" (which would just look like a residual category).
COMMON_GAPS = [g for g in CANONICAL_GAPS if g != "Other"]


# ── ESCO pool building ────────────────────────────────────────────────────────

def _esco_match(esco: dict, keywords: list[str], cap: int) -> list[dict]:
    """Filter ESCO to skills whose label contains any keyword. Return up to `cap`,
    preferring shorter labels (proxy for more general / common skills)."""
    needles = [kw.lower() for kw in keywords]
    matches = []
    for uri, entry in esco.items():
        label = entry.get("label", "")
        if not label:
            continue
        ll = label.lower()
        if any(n in ll for n in needles):
            matches.append({
                "uri": uri,
                "skill_name": label,
                "skill_type": entry.get("skillType", "skill/competence"),
            })
    matches.sort(key=lambda m: len(m["skill_name"]))
    return matches[:cap]


def build_pools(esco: dict) -> tuple[dict[str, list[dict]], list[dict]]:
    themed = {
        major: _esco_match(esco, kws, POOL_CAP_PER_GROUP)
        for major, kws in KEYWORDS_BY_MAJOR_GROUP.items()
    }
    generic = _esco_match(esco, GENERIC_KEYWORDS, GENERIC_POOL_CAP)
    return themed, generic


# ── Sampling helpers ──────────────────────────────────────────────────────────

def weighted_choice(items, weights):
    return random.choices(items, weights=weights, k=1)[0]


def pick_education() -> tuple[str, str]:
    levels, descs, weights = zip(*EDUCATION_DISTRIBUTION)
    idx = random.choices(range(len(levels)), weights=weights, k=1)[0]
    return levels[idx], descs[idx]


def isco_for_sector(country_config: dict, sector_slug: str) -> list[str]:
    return [
        isco for isco, wage in country_config.get("wage_data", {}).items()
        if not isco.startswith("_") and wage.get("sector") == sector_slug
    ]


def pick_primary_isco(country_config: dict) -> tuple[str, str]:
    """Sample an ISCO weighted by the sector's employment share."""
    sectors = country_config.get("sectors", {})
    sector_slugs = list(sectors.keys())
    weights = [sectors[s].get("share_employment", 0.01) for s in sector_slugs]

    for _ in range(20):
        slug = weighted_choice(sector_slugs, weights)
        candidates = isco_for_sector(country_config, slug)
        if candidates:
            return random.choice(candidates), slug

    all_iscos = [k for k in country_config.get("wage_data", {}) if not k.startswith("_")]
    isco = random.choice(all_iscos)
    return isco, country_config["wage_data"][isco].get("sector", "services")


def make_skills(primary_isco: str, themed_pools: dict[str, list[dict]], generic_pool: list[dict]) -> list[dict]:
    major = primary_isco[:1] if primary_isco else "5"
    themed_pool = themed_pools.get(major) or themed_pools.get("5") or []

    n_themed = random.randint(2, 4)
    n_generic = random.randint(1, 2)

    chosen: list[dict] = []
    if themed_pool:
        chosen += random.sample(themed_pool, k=min(n_themed, len(themed_pool)))
    if generic_pool:
        chosen += random.sample(generic_pool, k=min(n_generic, len(generic_pool)))

    return [
        {
            **skill,
            "level": random.choices(LEVELS, weights=LEVEL_WEIGHTS, k=1)[0],
            "evidence": "(synthetic seed)",
        }
        for skill in chosen
    ]


def make_matched_occupations(primary_isco: str) -> list[dict]:
    out = [{
        "isco_code": primary_isco,
        "title": ISCO_TITLES.get(primary_isco, primary_isco),
        "uri": None,
        "confidence": "high",
    }]
    if random.random() < 0.4:
        major = primary_isco[:1]
        siblings = [k for k in ISCO_TITLES if k.startswith(major) and k != primary_isco]
        if siblings:
            sib = random.choice(siblings)
            out.append({
                "isco_code": sib,
                "title": ISCO_TITLES[sib],
                "uri": None,
                "confidence": "medium",
            })
    return out


def make_automation_risk(primary_isco: str, country_config: dict, frey_osborne: dict) -> dict:
    raw = float((frey_osborne.get(primary_isco) or {}).get("raw_probability", 0.5))
    factor = country_config.get("automation_calibration", {}).get("infrastructure_factor", 1.0)
    calibrated = round(raw * factor, 3)
    if calibrated < 0.3:
        band = "low"
    elif calibrated < 0.7:
        band = "moderate"
    else:
        band = "high"
    return {
        "overall_risk": band,
        "calibrated_score": calibrated,
        "at_risk_tasks": [],
        "durable_skills": [],
        "adjacent_skills_for_resilience": [],
        "plain_language_summary": "(synthetic seed)",
    }


def make_opportunities(profile: dict, country_config: dict, frey_osborne: dict) -> list[dict]:
    candidates = _build_candidates(profile, country_config, frey_osborne)
    if not candidates:
        return []

    n = random.randint(3, 5)
    chosen = candidates[:n]
    out = []
    for c in chosen:
        gap = None
        if random.random() < 0.55:
            gap = random.choice(COMMON_GAPS)
        out.append({
            "title": ISCO_TITLES.get(c["isco_code"], c["title"]),
            "opportunity_type": random.choice(OPPORTUNITY_TYPES),
            "isco_code": c["isco_code"],
            "sector": c.get("sector"),
            "skill_gap": gap,
            "sector_growth_pct": c.get("sector_growth_pct"),
        })
    return out


# ── Main ──────────────────────────────────────────────────────────────────────

def seed_country(
    country_code: str,
    country_config: dict,
    frey_osborne: dict,
    themed_pools: dict[str, list[dict]],
    generic_pool: list[dict],
    n: int,
) -> int:
    regions = country_config.get("regions") or [{"code": None}]
    region_codes = [r.get("code") for r in regions]
    region_weights = [3 if r.get("type") == "urban_metro" else 1 for r in regions]

    inserted = 0
    for _ in range(n):
        primary_isco, sector_slug = pick_primary_isco(country_config)
        isced_level, isced_desc = pick_education()

        skills_profile = {
            "matched_occupations": make_matched_occupations(primary_isco),
            "skills": make_skills(primary_isco, themed_pools, generic_pool),
            "education_level": {
                "isced_level": isced_level,
                "description": isced_desc,
                "local_credential": "(synthetic)",
            },
            "languages": [{"language": country_config["language"]["primary"], "proficiency": "fluent"}],
            "portable_summary": f"(synthetic profile in {sector_slug} sector)",
        }
        risk = make_automation_risk(primary_isco, country_config, frey_osborne)
        opportunities = make_opportunities(skills_profile, country_config, frey_osborne)

        repository.insert_profile(
            skills_profile=skills_profile,
            automation_risk=risk,
            opportunities=opportunities,
            country_code=country_code,
            region=weighted_choice(region_codes, region_weights),
            sector_hint=sector_slug,
            source="synthetic",
        )
        inserted += 1
    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--countries", nargs="+", default=["GH", "IN"])
    parser.add_argument("--per-country", type=int, default=300)
    parser.add_argument("--no-reset", action="store_true",
                        help="Append rather than replacing existing synthetic rows")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    init_db()

    countries = json.loads((DATA_DIR / "countries.json").read_text())
    frey = json.loads((DATA_DIR / "frey_osborne.json").read_text())
    esco = json.loads((DATA_DIR / "esco_skills.json").read_text())

    themed_pools, generic_pool = build_pools(esco)
    print("ESCO pool sizes:", {k: len(v) for k, v in themed_pools.items()},
          "| generic:", len(generic_pool))

    if not args.no_reset:
        for cc in args.countries:
            wiped = repository.delete_synthetic(cc)
            print(f"[{cc}] wiped {wiped} synthetic rows")

    for cc in args.countries:
        if cc not in countries:
            print(f"[{cc}] not in countries.json — skipping")
            continue
        n = seed_country(cc, countries[cc], frey, themed_pools, generic_pool, args.per_country)
        print(f"[{cc}] inserted {n} synthetic profiles")


if __name__ == "__main__":
    main()
