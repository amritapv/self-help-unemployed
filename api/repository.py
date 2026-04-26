"""
Data-access layer for profiles + opportunities.

Two responsibilities:
  - Persist a complete user record (skills profile + automation risk + opportunities)
  - Aggregate persisted records for the policymaker /report endpoint

Hides the storage backend from callers — today SQLite, tomorrow Supabase/Postgres
should be a one-file change.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Optional

from api.db import connect, init_db


# ── Writes ────────────────────────────────────────────────────────────────────

def insert_profile(
    *,
    skills_profile: dict[str, Any],
    automation_risk: dict[str, Any],
    opportunities: list[dict[str, Any]],
    country_code: str,
    region: Optional[str] = None,
    sector_hint: Optional[str] = None,
    source: str = "live",
) -> str:
    """Persist one assessed user. Returns the new profile_id."""
    init_db()
    profile_id = str(uuid.uuid4())

    edu = skills_profile.get("education_level") or {}
    isced = edu.get("isced_level")

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO profiles (
                id, country_code, region, sector_hint, isced_level,
                automation_risk_band, automation_calibrated_score, portable_summary,
                source, raw_profile
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile_id,
                country_code,
                region,
                sector_hint,
                isced,
                automation_risk.get("overall_risk"),
                automation_risk.get("calibrated_score"),
                skills_profile.get("portable_summary"),
                source,
                json.dumps({"skills_profile": skills_profile, "automation_risk": automation_risk}),
            ),
        )

        for s in skills_profile.get("skills") or []:
            conn.execute(
                "INSERT INTO profile_skills (profile_id, skill_name, skill_type, level) VALUES (?, ?, ?, ?)",
                (profile_id, s.get("skill_name"), s.get("skill_type"), s.get("level")),
            )

        for o in skills_profile.get("matched_occupations") or []:
            conn.execute(
                "INSERT INTO profile_occupations (profile_id, isco_code, title, confidence) VALUES (?, ?, ?, ?)",
                (profile_id, o.get("isco_code"), o.get("title"), str(o.get("confidence", ""))),
            )

        for opp in opportunities or []:
            has_gap = 1 if opp.get("skill_gap") else 0
            conn.execute(
                """
                INSERT INTO profile_opportunities (
                    profile_id, title, opportunity_type, isco_code, sector,
                    has_skill_gap, skill_gap_text, sector_growth_pct
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile_id,
                    opp.get("title"),
                    opp.get("opportunity_type"),
                    opp.get("isco_code"),
                    opp.get("sector"),
                    has_gap,
                    opp.get("skill_gap"),
                    opp.get("sector_growth_pct"),
                ),
            )

    return profile_id


def attach_opportunities(
    profile_id: str,
    opportunities: list[dict[str, Any]],
) -> bool:
    """Replace any existing opportunity rows for `profile_id` with the new set.

    Returns True if the profile exists and rows were written, False if the
    profile_id is unknown (caller can fall back to a fresh insert).
    """
    init_db()
    with connect() as conn:
        row = conn.execute("SELECT 1 FROM profiles WHERE id = ?", (profile_id,)).fetchone()
        if not row:
            return False
        conn.execute("DELETE FROM profile_opportunities WHERE profile_id = ?", (profile_id,))
        for opp in opportunities or []:
            has_gap = 1 if opp.get("skill_gap") else 0
            conn.execute(
                """
                INSERT INTO profile_opportunities (
                    profile_id, title, opportunity_type, isco_code, sector,
                    has_skill_gap, skill_gap_text, sector_growth_pct
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile_id,
                    opp.get("title"),
                    opp.get("opportunity_type"),
                    opp.get("isco_code"),
                    opp.get("sector"),
                    has_gap,
                    opp.get("skill_gap"),
                    opp.get("sector_growth_pct"),
                ),
            )
    return True


# ── Telegram session storage ──────────────────────────────────────────────────

def get_telegram_session(chat_id: int) -> Optional[dict]:
    """Load a telegram session row. Returns None if no session exists."""
    init_db()
    with connect() as conn:
        row = conn.execute(
            "SELECT chat_id, messages, collected_data, profile_id, country_code, language "
            "FROM telegram_sessions WHERE chat_id = ?",
            (chat_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "chat_id": row["chat_id"],
        "messages": json.loads(row["messages"]) if row["messages"] else [],
        "collected_data": json.loads(row["collected_data"]) if row["collected_data"] else None,
        "profile_id": row["profile_id"],
        "country_code": row["country_code"],
        "language": row["language"],
    }


def upsert_telegram_session(
    chat_id: int,
    messages: list,
    collected_data: Optional[dict] = None,
    profile_id: Optional[str] = None,
    country_code: str = "GH",
    language: str = "en",
) -> None:
    init_db()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO telegram_sessions
                (chat_id, messages, collected_data, profile_id, country_code, language, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(chat_id) DO UPDATE SET
                messages = excluded.messages,
                collected_data = excluded.collected_data,
                profile_id = excluded.profile_id,
                country_code = excluded.country_code,
                language = excluded.language,
                updated_at = excluded.updated_at
            """,
            (
                chat_id,
                json.dumps(messages),
                json.dumps(collected_data) if collected_data is not None else None,
                profile_id,
                country_code,
                language,
            ),
        )


def delete_telegram_session(chat_id: int) -> None:
    init_db()
    with connect() as conn:
        conn.execute("DELETE FROM telegram_sessions WHERE chat_id = ?", (chat_id,))


def delete_synthetic(country_code: Optional[str] = None) -> int:
    """Wipe synthetic seed rows. Returns count deleted."""
    init_db()
    with connect() as conn:
        if country_code:
            cur = conn.execute(
                "DELETE FROM profiles WHERE source = 'synthetic' AND country_code = ?",
                (country_code,),
            )
        else:
            cur = conn.execute("DELETE FROM profiles WHERE source = 'synthetic'")
        return cur.rowcount


# ── Reads (aggregation for /report) ───────────────────────────────────────────

def _profile_filter(country_code: str, region: Optional[str], sector: Optional[str]) -> tuple[str, list]:
    """Build a WHERE clause + params restricting to the profile cohort.

    If sector is given, restrict to profiles that have at least one opportunity in that sector.
    """
    where = ["p.country_code = ?"]
    params: list = [country_code]
    if region:
        where.append("p.region = ?")
        params.append(region)
    if sector:
        where.append(
            "EXISTS (SELECT 1 FROM profile_opportunities po WHERE po.profile_id = p.id AND po.sector = ?)"
        )
        params.append(sector)
    return " AND ".join(where), params


def count_profiles(country_code: str, region: Optional[str], sector: Optional[str]) -> int:
    where, params = _profile_filter(country_code, region, sector)
    with connect() as conn:
        row = conn.execute(f"SELECT COUNT(*) AS n FROM profiles p WHERE {where}", params).fetchone()
    return int(row["n"])


def top_skills(country_code: str, region: Optional[str], sector: Optional[str], limit: int = 10) -> list[dict]:
    where, params = _profile_filter(country_code, region, sector)
    sql = f"""
        SELECT s.skill_name AS skill, COUNT(*) AS count
        FROM profile_skills s
        JOIN profiles p ON p.id = s.profile_id
        WHERE {where}
        GROUP BY s.skill_name
        ORDER BY count DESC
        LIMIT ?
    """
    with connect() as conn:
        rows = conn.execute(sql, [*params, limit]).fetchall()
        total = count_profiles(country_code, region, sector) or 1
    return [
        {"skill": r["skill"], "count": r["count"], "pct": round(r["count"] / total, 3)}
        for r in rows
    ]


def education_distribution(country_code: str, region: Optional[str], sector: Optional[str]) -> dict[str, float]:
    where, params = _profile_filter(country_code, region, sector)
    sql = f"""
        SELECT isced_level, COUNT(*) AS n
        FROM profiles p
        WHERE {where} AND isced_level IS NOT NULL
        GROUP BY isced_level
    """
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    total = sum(r["n"] for r in rows) or 1
    return {r["isced_level"]: round(r["n"] / total, 3) for r in rows}


def automation_exposure(country_code: str, region: Optional[str], sector: Optional[str]) -> dict[str, dict]:
    where, params = _profile_filter(country_code, region, sector)
    band_sql = f"""
        SELECT automation_risk_band AS band, COUNT(*) AS n
        FROM profiles p
        WHERE {where} AND automation_risk_band IS NOT NULL
        GROUP BY automation_risk_band
    """
    occ_sql = f"""
        SELECT po.title AS title, COUNT(*) AS n
        FROM profile_occupations po
        JOIN profiles p ON p.id = po.profile_id
        WHERE {where} AND p.automation_risk_band = ?
        GROUP BY po.title
        ORDER BY n DESC
        LIMIT 3
    """
    with connect() as conn:
        band_rows = conn.execute(band_sql, params).fetchall()
        total = sum(r["n"] for r in band_rows) or 1
        result = {"high_risk": {"pct": 0, "top_occupations": []},
                  "moderate_risk": {"pct": 0, "top_occupations": []},
                  "low_risk": {"pct": 0, "top_occupations": []}}
        for r in band_rows:
            band = r["band"]
            key = f"{band}_risk" if band in ("high", "moderate", "low") else None
            if key is None:
                continue
            occ_rows = conn.execute(occ_sql, [*params, band]).fetchall()
            result[key] = {
                "pct": round(r["n"] / total, 3),
                "top_occupations": [o["title"] for o in occ_rows if o["title"]],
            }
    return result


def opportunity_gaps(
    country_code: str,
    region: Optional[str],
    sector: Optional[str],
    sectors_meta: dict[str, dict],
) -> dict[str, Any]:
    """Compute highest-growth sectors (from opportunities present in cohort)
    and biggest skill gaps."""
    where, params = _profile_filter(country_code, region, sector)

    sector_sql = f"""
        SELECT po.sector AS sector, COUNT(*) AS n
        FROM profile_opportunities po
        JOIN profiles p ON p.id = po.profile_id
        WHERE {where} AND po.sector IS NOT NULL
        GROUP BY po.sector
    """
    gap_sql = f"""
        SELECT po.skill_gap_text AS gap, COUNT(*) AS n
        FROM profile_opportunities po
        JOIN profiles p ON p.id = po.profile_id
        WHERE {where} AND po.has_skill_gap = 1 AND po.skill_gap_text IS NOT NULL
        GROUP BY po.skill_gap_text
        ORDER BY n DESC
        LIMIT 5
    """
    with connect() as conn:
        sector_rows = conn.execute(sector_sql, params).fetchall()
        gap_rows = conn.execute(gap_sql, params).fetchall()

    # Rank sectors present in the cohort by growth_annual from country config
    ranked = sorted(
        ({"sector": r["sector"], "count": r["n"], "growth": (sectors_meta.get(r["sector"]) or {}).get("growth_annual", 0)}
         for r in sector_rows),
        key=lambda x: x["growth"],
        reverse=True,
    )
    highest_growth = [s["sector"] for s in ranked[:3]]
    biggest_gaps = [r["gap"] for r in gap_rows]

    return {
        "highest_growth_sectors": highest_growth,
        "biggest_skill_gaps": biggest_gaps,
    }
