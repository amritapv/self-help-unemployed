"""
Policymaker API: Aggregate reporting.

Reads from the persisted profile store via api.repository and merges in the
country's econometric signals (which live in countries.json, not the DB).
"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from api import repository


def generate_report(
    country_config: dict[str, Any],
    region: Optional[str] = None,
    sector: Optional[str] = None,
) -> dict[str, Any]:
    """Build the /report payload by aggregating persisted profiles."""
    country_code = country_config.get("country_code", "")
    sectors_meta = country_config.get("sectors", {})

    profiles_assessed = repository.count_profiles(country_code, region, sector)

    if profiles_assessed == 0:
        empty_meta = {
            "country": country_config.get("country_name", country_code),
            "region": region,
            "sector": sector,
            "profiles_assessed": 0,
            "report_date": date.today().isoformat(),
            "note": "No assessed profiles match these filters yet.",
        }
        return {
            "report_meta": empty_meta,
            "skills_distribution": {"top_skills": [], "education_levels": {}},
            "automation_exposure": {
                "high_risk": {"pct": 0, "top_occupations": []},
                "moderate_risk": {"pct": 0, "top_occupations": []},
                "low_risk": {"pct": 0, "top_occupations": []},
            },
            "opportunity_gaps": {
                "highest_growth_sectors": [],
                "biggest_skill_gaps": [],
            },
            "econometric_signals": _econometric_signals(country_config),
        }

    return {
        "report_meta": {
            "country": country_config.get("country_name", country_code),
            "region": region,
            "sector": sector,
            "profiles_assessed": profiles_assessed,
            "report_date": date.today().isoformat(),
        },
        "skills_distribution": {
            "top_skills": repository.top_skills(country_code, region, sector),
            "education_levels": repository.education_distribution(country_code, region, sector),
        },
        "automation_exposure": repository.automation_exposure(country_code, region, sector),
        "opportunity_gaps": repository.opportunity_gaps(country_code, region, sector, sectors_meta),
        "econometric_signals": _econometric_signals(country_config),
    }


def _econometric_signals(country_config: dict[str, Any]) -> dict[str, Any]:
    demo = country_config.get("demographics", {})
    sectors = country_config.get("sectors", {})
    return {
        "youth_unemployment": demo.get("youth_unemployment_rate"),
        "informality_rate": demo.get("informality_rate"),
        "sector_growth": {name: s.get("growth_annual") for name, s in sectors.items()},
    }
