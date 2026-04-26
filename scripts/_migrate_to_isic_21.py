"""One-off migration: expand the per-country `sectors` block from 10 LMIC-collapsed
slices to all 21 ISIC Rev.4 sections. Also retags the two wage_data ISCOs that
pointed at the removed `services` catch-all (7421 -> other_services,
4110 -> admin_support), and rewrites platform_config.sector_translations.en.

Run once: `python scripts/_migrate_to_isic_21.py`. Safe to delete after the
migration commit lands; kept here for auditability.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ──────────────────────────────────────────────────────────────────────────────
# Sector definitions: friendly noun phrase + LMIC default growth/share/informality
# ──────────────────────────────────────────────────────────────────────────────

# slug -> friendly English noun phrase (for platform_config.sector_translations.en)
SECTOR_LABELS = {
    "agriculture":           "farming, forestry, and fishing",
    "mining":                "mining and quarrying",
    "manufacturing":         "factory and manufacturing work",
    "utilities":             "electricity, gas, and renewable energy",
    "water_waste":           "water, sanitation, and waste",
    "construction":          "building and construction",
    "retail":                "shops and selling",
    "transport":             "transport, delivery, and driving",
    "hospitality":           "hotels, restaurants, and food service",
    "ict":                   "tech and digital jobs",
    "finance":               "banking and finance",
    "real_estate":           "real estate",
    "professional_services": "professional and technical services",
    "admin_support":         "administrative and support work",
    "public_admin":          "public administration",
    "education":             "teaching",
    "healthcare":            "health and care work",
    "arts_recreation":       "arts, entertainment, and recreation",
    "other_services":        "repair shops and personal services",
    "household":             "household and domestic work",
    "extraterritorial":      "international organisations",
}

# Sane LMIC defaults — overridden per country below.
DEFAULTS = {
    "agriculture":           {"growth_annual": 0.025, "share_employment": 0.20,  "informal_share": 0.90},
    "mining":                {"growth_annual": 0.03,  "share_employment": 0.015, "informal_share": 0.50},
    "manufacturing":         {"growth_annual": 0.05,  "share_employment": 0.12,  "informal_share": 0.55},
    "utilities":             {"growth_annual": 0.20,  "share_employment": 0.008, "informal_share": 0.25},
    "water_waste":           {"growth_annual": 0.05,  "share_employment": 0.01,  "informal_share": 0.40},
    "construction":          {"growth_annual": 0.06,  "share_employment": 0.07,  "informal_share": 0.80},
    "retail":                {"growth_annual": 0.05,  "share_employment": 0.17,  "informal_share": 0.65},
    "transport":             {"growth_annual": 0.05,  "share_employment": 0.07,  "informal_share": 0.70},
    "hospitality":           {"growth_annual": 0.07,  "share_employment": 0.05,  "informal_share": 0.65},
    "ict":                   {"growth_annual": 0.13,  "share_employment": 0.04,  "informal_share": 0.30},
    "finance":               {"growth_annual": 0.08,  "share_employment": 0.025, "informal_share": 0.10},
    "real_estate":           {"growth_annual": 0.06,  "share_employment": 0.012, "informal_share": 0.30},
    "professional_services": {"growth_annual": 0.07,  "share_employment": 0.03,  "informal_share": 0.30},
    "admin_support":         {"growth_annual": 0.05,  "share_employment": 0.025, "informal_share": 0.40},
    "public_admin":          {"growth_annual": 0.03,  "share_employment": 0.04,  "informal_share": 0.10},
    "education":             {"growth_annual": 0.04,  "share_employment": 0.04,  "informal_share": 0.20},
    "healthcare":            {"growth_annual": 0.06,  "share_employment": 0.035, "informal_share": 0.35},
    "arts_recreation":       {"growth_annual": 0.05,  "share_employment": 0.012, "informal_share": 0.55},
    "other_services":        {"growth_annual": 0.05,  "share_employment": 0.025, "informal_share": 0.70},
    "household":             {"growth_annual": 0.025, "share_employment": 0.02,  "informal_share": 0.92},
    "extraterritorial":      {"growth_annual": 0.0,   "share_employment": 0.001, "informal_share": 0.0},
}

# Per-country overrides — only the fields where the difference matters for the
# matcher. Anything not listed inherits from DEFAULTS.
OVERRIDES = {
    "GH": {
        "agriculture":   {"share_employment": 0.30, "informal_share": 0.96},
        "mining":        {"share_employment": 0.025, "growth_annual": 0.04, "informal_share": 0.55},
        "manufacturing": {"share_employment": 0.13, "growth_annual": 0.06, "informal_share": 0.65},
        "construction":  {"share_employment": 0.05, "growth_annual": 0.07, "informal_share": 0.85},
        "retail":        {"share_employment": 0.18, "informal_share": 0.92},
        "ict":           {"growth_annual": 0.14},
        "utilities":     {"growth_annual": 0.22},  # renewable boom
        "education":     {"share_employment": 0.04, "growth_annual": 0.04, "informal_share": 0.30},
        "healthcare":    {"share_employment": 0.03, "informal_share": 0.45},
    },
    "IN": {
        "agriculture":           {"share_employment": 0.42, "informal_share": 0.95},
        "manufacturing":         {"share_employment": 0.11, "growth_annual": 0.08, "informal_share": 0.75},
        "construction":          {"share_employment": 0.12, "growth_annual": 0.09, "informal_share": 0.90},
        "retail":                {"share_employment": 0.10, "growth_annual": 0.06, "informal_share": 0.85},
        "ict":                   {"growth_annual": 0.18, "informal_share": 0.20},  # BPO formal
        "utilities":             {"growth_annual": 0.30},
        "professional_services": {"growth_annual": 0.10},
        "education":             {"share_employment": 0.04, "growth_annual": 0.05, "informal_share": 0.25},
        "healthcare":            {"share_employment": 0.03, "growth_annual": 0.08, "informal_share": 0.40},
    },
    "MX": {
        "agriculture":   {"share_employment": 0.13, "informal_share": 0.85},
        "mining":        {"share_employment": 0.02, "informal_share": 0.30},
        "manufacturing": {"share_employment": 0.16, "growth_annual": 0.04, "informal_share": 0.35},
        "construction":  {"share_employment": 0.08, "growth_annual": 0.05, "informal_share": 0.65},
        "retail":        {"share_employment": 0.18, "growth_annual": 0.04, "informal_share": 0.55},
        "hospitality":   {"share_employment": 0.10, "growth_annual": 0.07, "informal_share": 0.55},  # Cancún + tourism
        "ict":           {"share_employment": 0.05, "growth_annual": 0.10},
        "utilities":     {"growth_annual": 0.20},
    },
    "PH": {
        "agriculture":   {"share_employment": 0.23, "informal_share": 0.85},
        "manufacturing": {"share_employment": 0.08, "growth_annual": 0.05, "informal_share": 0.40},
        "construction":  {"share_employment": 0.09, "growth_annual": 0.06, "informal_share": 0.65},
        "retail":        {"share_employment": 0.15, "growth_annual": 0.05, "informal_share": 0.70},
        "hospitality":   {"share_employment": 0.08, "growth_annual": 0.08, "informal_share": 0.65},
        "ict":           {"share_employment": 0.04, "growth_annual": 0.15, "informal_share": 0.30},  # BPO
        "utilities":     {"growth_annual": 0.18},
    },
    "CO": {
        "agriculture":           {"share_employment": 0.16, "informal_share": 0.85},
        "mining":                {"share_employment": 0.015, "informal_share": 0.40},
        "manufacturing":         {"share_employment": 0.12, "growth_annual": 0.04, "informal_share": 0.45},
        "construction":          {"share_employment": 0.07, "growth_annual": 0.05, "informal_share": 0.65},
        "retail":                {"share_employment": 0.18, "growth_annual": 0.04, "informal_share": 0.55},
        "hospitality":           {"share_employment": 0.06, "growth_annual": 0.08, "informal_share": 0.55},  # Cartagena/Medellín
        "ict":                   {"share_employment": 0.04, "growth_annual": 0.12, "informal_share": 0.40},
        "utilities":             {"growth_annual": 0.18},
    },
}

# ──────────────────────────────────────────────────────────────────────────────
# wage_data retags — moving from old slugs to ISIC 21
# ──────────────────────────────────────────────────────────────────────────────

# Per-ISCO target sector slug after the migration. Any ISCO not listed keeps
# whatever it currently has (which had better still be in the 21-slug set).
WAGE_RETAGS = {
    "7421": "other_services",   # Electronics/mobile repair shops -> ISIC S
    "4110": "admin_support",    # General office clerks -> ISIC N
    # Existing tags that are still valid in the 21-slug set:
    # 2519, 3512, 3514 -> ict
    # 7411, 7115     -> construction
    # 7412           -> manufacturing
    # 5223, 9520     -> retail
    # 6111, 9211     -> agriculture
    # 5311           -> education
}


def _build_sectors_for(cc: str) -> dict[str, dict[str, float]]:
    overrides = OVERRIDES.get(cc, {})
    out: dict[str, dict[str, float]] = {}
    for slug in SECTOR_LABELS:
        base = dict(DEFAULTS[slug])
        base.update(overrides.get(slug, {}))
        out[slug] = base
    return out


def main() -> None:
    countries_path = ROOT / "data" / "countries.json"
    config_path = ROOT / "data" / "platform_config.json"

    countries = json.loads(countries_path.read_text(encoding="utf-8"))
    for cc in ("GH", "IN", "MX", "PH", "CO"):
        if cc not in countries:
            print(f"  ! {cc} missing from countries.json — skipping")
            continue
        countries[cc]["sectors"] = _build_sectors_for(cc)
        wage = countries[cc].get("wage_data", {})
        retagged = 0
        for isco, target in WAGE_RETAGS.items():
            entry = wage.get(isco)
            if isinstance(entry, dict) and entry.get("sector") != target:
                entry["sector"] = target
                retagged += 1
        print(f"  {cc}: 21 sectors, {retagged} wage_data retags")

    countries_path.write_text(
        json.dumps(countries, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"  -> {countries_path.name}")

    config = json.loads(config_path.read_text(encoding="utf-8"))
    config.setdefault("sector_translations", {})["en"] = dict(SECTOR_LABELS)
    config_path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"  -> {config_path.name} (21 sector labels)")


if __name__ == "__main__":
    main()
