"""
Module 01: Skills Signal Engine
================================
Takes user input (education, experience, skills, additional_information)
and maps it to a standardized ESCO / ISCO-08 skills profile using
keyword pre-filtering + Claude API.

Input JSON:
  {
    "education":               "WASSCE, secondary school",
    "experience":              "5 years phone repair",
    "skills":                  "soldering, Python basics",
    "additional_information":  "speaks Twi and English",
    "country_code":            "GH"   # optional, default GH
  }

Output JSON:
  {
    "matched_occupations": [...],
    "skills":              [...],
    "education_level":     {...},
    "languages":           [...],
    "portable_summary":    "...",
    "human_readable":      "..."   # plain language for the user
  }
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import zipfile
from pathlib import Path
from typing import Any

import anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Override via env var if the zip lives elsewhere
ESCO_ZIP = Path(
    os.getenv(
        "ESCO_ZIP_PATH",
        str(Path.home() / "Downloads" / "ESCO dataset - v1.2.1 - classification - en - csv.zip"),
    )
)

# Cached parsed data (loaded once on first call)
_cache: dict[str, Any] = {}


# ── Data loading ───────────────────────────────────────────────────────────────

def _iter_csv(filename: str):
    """
    Yield rows (as dicts) from a CSV file.
    Tries, in order:
      1. data/<filename>          (pre-extracted)
      2. ESCO_ZIP                 (read directly from the zip)
    """
    local = DATA_DIR / filename
    if local.exists():
        with open(local, encoding="utf-8", newline="") as fh:
            yield from csv.DictReader(fh)
        return

    if ESCO_ZIP.exists():
        with zipfile.ZipFile(ESCO_ZIP) as zf:
            with zf.open(filename) as raw:
                text = io.TextIOWrapper(raw, encoding="utf-8", newline="")
                yield from csv.DictReader(text)
        return

    raise FileNotFoundError(
        f"ESCO data not found.\n"
        f"  Looked for: {local}\n"
        f"  And zip:    {ESCO_ZIP}\n"
        f"  Download from https://esco.ec.europa.eu/en/use-esco/download"
    )


def _load_skills() -> dict[str, dict]:
    """
    Returns {uri: {label, skillType, description, altLabels: [str]}}
    Cached after first load; also saves to data/esco_skills.json for speed.
    """
    if "skills" in _cache:
        return _cache["skills"]

    json_path = DATA_DIR / "esco_skills.json"
    if json_path.exists() and json_path.stat().st_size > 0:
        with open(json_path, encoding="utf-8") as f:
            _cache["skills"] = json.load(f)
        return _cache["skills"]

    print("Loading ESCO skills (first run — will cache to data/esco_skills.json)…")
    skills: dict[str, dict] = {}
    for row in _iter_csv("skills_en.csv"):
        uri = row.get("conceptUri", "").strip()
        if not uri:
            continue
        skills[uri] = {
            "label": row.get("preferredLabel", "").strip(),
            "skillType": row.get("skillType", "").strip(),
            "description": row.get("description", "").strip()[:300],
            "altLabels": [
                a.strip()
                for a in re.split(r"[\n\r]+", row.get("altLabels", ""))
                if a.strip()
            ],
        }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(skills, f)
    print(f"  ✓ Loaded {len(skills):,} skills → saved to {json_path}")

    _cache["skills"] = skills
    return skills


def _load_occupations() -> dict[str, dict]:
    """
    Returns {uri: {label, iscoCode, description, altLabels: [str]}}
    Cached after first load; also saves to data/isco08_taxonomy.json.
    """
    if "occupations" in _cache:
        return _cache["occupations"]

    json_path = DATA_DIR / "isco08_taxonomy.json"
    if json_path.exists() and json_path.stat().st_size > 0:
        with open(json_path, encoding="utf-8") as f:
            _cache["occupations"] = json.load(f)
        return _cache["occupations"]

    print("Loading ESCO occupations (first run — will cache to data/isco08_taxonomy.json)…")
    occupations: dict[str, dict] = {}
    for row in _iter_csv("occupations_en.csv"):
        uri = row.get("conceptUri", "").strip()
        if not uri:
            continue
        occupations[uri] = {
            "label": row.get("preferredLabel", "").strip(),
            "iscoCode": row.get("iscoGroup", "").strip(),
            "code": row.get("code", "").strip(),
            "description": row.get("description", "").strip()[:300],
            "altLabels": [
                a.strip()
                for a in re.split(r"[\n\r]+", row.get("altLabels", ""))
                if a.strip()
            ],
        }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(occupations, f)
    print(f"  ✓ Loaded {len(occupations):,} occupations → saved to {json_path}")

    _cache["occupations"] = occupations
    return occupations


# ── Candidate pre-filtering ───────────────────────────────────────────────────

def _find_candidates(user_text: str, skills: dict, occupations: dict, n: int = 60) -> list[dict]:
    """
    Keyword overlap scoring to find the ESCO entries most relevant to
    the user's free-text input. Returns top-N to pass to Claude so we
    don't blow the context window with 13,000+ entries.
    """
    words = set(re.findall(r"\b[a-z]{4,}\b", user_text.lower()))
    if not words:
        return []

    scored: list[tuple[int, str, dict]] = []

    for uri, entry in {**skills, **occupations}.items():
        label = entry["label"].lower()
        alts = " ".join(entry.get("altLabels", [])).lower()
        desc = entry.get("description", "").lower()
        haystack = f"{label} {alts} {desc}"

        score = sum(1 for w in words if w in haystack)
        if score > 0:
            scored.append((score, uri, entry))

    scored.sort(key=lambda x: -x[0])

    return [
        {
            "uri": uri,
            "label": entry["label"],
            "type": entry.get("skillType") or entry.get("iscoCode", ""),
            "description": entry.get("description", "")[:150],
        }
        for _, uri, entry in scored[:n]
    ]


# ── Main entry point ──────────────────────────────────────────────────────────

def assess_skills(
    education: str,
    experience: str,
    skills: str,
    additional_information: str,
    country_code: str = "GH",
    countries_config: dict | None = None,
) -> dict:
    """
    Map a user's self-described profile to a standardised ESCO/ISCO-08
    skills profile.

    Args:
        education:              Free-text description of formal education.
        experience:             Free-text description of work experience.
        skills:                 Free-text list of self-reported skills.
        additional_information: Any other relevant context.
        country_code:           ISO-2 country code (e.g. "GH", "IN").
        countries_config:       Parsed countries.json dict (optional but
                                recommended for education taxonomy mapping).

    Returns:
        dict with keys:
          matched_occupations, skills, education_level, languages,
          portable_summary, human_readable
    """

    # 1. Load ESCO data
    esco_skills = _load_skills()
    esco_occupations = _load_occupations()

    # 2. Country context
    country_cfg: dict = {}
    if countries_config and country_code in countries_config:
        country_cfg = countries_config[country_code]

    country_name = country_cfg.get("country_name", country_code)
    edu_taxonomy = country_cfg.get("education_taxonomy", [])
    edu_taxonomy_text = (
        "\n".join(
            f"  - {e['local']} → ISCED Level {e['isced']} ({e['label']})"
            for e in edu_taxonomy
        )
        if edu_taxonomy
        else "  - Use standard ISCED levels 0–8"
    )

    # 3. Keyword pre-filter: get ~60 ESCO candidates to send to Claude
    user_text = f"{education} {experience} {skills} {additional_information}"
    candidates = _find_candidates(user_text, esco_skills, esco_occupations, n=60)
    candidates_text = "\n".join(
        f"- {c['label']} | type: {c['type']} | uri: {c['uri']}"
        + (f" | {c['description']}" if c["description"] else "")
        for c in candidates
    )

    # 4. Call Claude API
    client = anthropic.Anthropic()

    system_prompt = f"""You are a skills assessment engine for UNMAPPED — a platform helping young people in low- and middle-income countries get their real skills formally recognised.

Your task: map a person's self-described background to a structured ESCO / ISCO-08 skills profile.

RULES:
- Treat informal and self-taught skills as fully valid — "I fix phones" maps to real ESCO skills.
- Only use ESCO URIs from the candidate list provided. If no URI fits, set uri to null.
- confidence: "high" = explicitly stated, "medium" = strongly implied, "low" = inferred.
- level: "basic" | "intermediate" | "advanced"
- skill_type: "knowledge" | "skill/competence" | "attitude"
- isced_level: integer string "0"–"8"
- Write portable_summary in second person ("You have...", "Your skills...") in plain English the user can read and share with an employer.

Country context: {country_name}
Education taxonomy for this country:
{edu_taxonomy_text}

Respond with ONLY a JSON object — no prose, no markdown fences — matching this schema exactly:
{{
  "matched_occupations": [
    {{"isco_code": "XXXX", "title": "string", "uri": "string or null", "confidence": "high|medium|low"}}
  ],
  "skills": [
    {{
      "uri": "string or null",
      "skill_name": "string",
      "skill_type": "knowledge|skill/competence|attitude",
      "level": "basic|intermediate|advanced",
      "evidence": "exact phrase from input that demonstrates this skill"
    }}
  ],
  "education_level": {{
    "isced_level": "string",
    "description": "plain English description",
    "local_credential": "as the person described it"
  }},
  "languages": [
    {{"language": "string", "proficiency": "native|fluent|conversational|basic"}}
  ],
  "portable_summary": "3-4 sentence plain-language summary Amara can share with employers or training programs"
}}"""

    user_message = f"""Map this person's background to a structured ESCO / ISCO-08 profile.

EDUCATION:
{education}

WORK EXPERIENCE:
{experience}

SKILLS (self-described):
{skills}

ADDITIONAL INFORMATION:
{additional_information}

CANDIDATE ESCO ENTRIES (only use URIs from this list):
{candidates_text}"""

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    # 5. Parse response — strip accidental markdown fences
    raw = response.content[0].text.strip()
    raw = re.sub(r"^```[a-z]*\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        profile = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Claude returned non-JSON:\n{raw}") from exc

    # 6. Add plain-language human-readable card
    profile["human_readable"] = _build_human_readable(profile, country_name)

    return profile


# ── Human-readable formatter ──────────────────────────────────────────────────

def _build_human_readable(profile: dict, country_name: str) -> str:
    """
    Turn the structured profile into a plain-English card that the user
    can read, share, or print — no jargon, no raw URIs.
    """
    occupations = profile.get("matched_occupations", [])
    skills      = profile.get("skills", [])
    education   = profile.get("education_level", {})
    languages   = profile.get("languages", [])
    summary     = profile.get("portable_summary", "")

    lines: list[str] = ["━━━ YOUR SKILLS PROFILE ━━━", ""]

    if summary:
        lines += [summary, ""]

    if education:
        cred  = education.get("local_credential", "")
        desc  = education.get("description", "")
        isced = education.get("isced_level", "")
        lines.append(f"Your education: {cred} — {desc} (ISCED {isced})")

    if languages:
        lang_str = ", ".join(
            f"{lg['language']} ({lg['proficiency']})" for lg in languages
        )
        lines.append(f"Your languages: {lang_str}")

    if education or languages:
        lines.append("")

    top_skills = [s for s in skills if s.get("level") in ("advanced", "intermediate") and s.get("uri")][:6]
    if top_skills:
        lines.append("Your strongest skills:")
        for s in top_skills:
            lines.append(f"  • {s['skill_name']}  [{s['level']}]")
        lines.append("")

    lines += [
        "",
        "Your profile uses international standards (ISCO-08 / ESCO) "
        "recognised across 90+ countries.",
    ]

    return "\n".join(lines)


# ── Quick smoke test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    sample_countries = {
        "GH": {
            "country_name": "Ghana",
            "education_taxonomy": [
                {"local": "BECE",    "isced": "2", "label": "Lower secondary"},
                {"local": "WASSCE",  "isced": "3", "label": "Upper secondary"},
                {"local": "HND",     "isced": "5", "label": "Short-cycle tertiary"},
            ],
        }
    }

    result = assess_skills(
        education="I completed my WASSCE (secondary school) in 2019.",
        experience=(
            "I've been running my own phone repair shop since I was 17. "
            "I fix screens, replace batteries, diagnose circuit problems, "
            "and sometimes recover data from water-damaged phones."
        ),
        skills=(
            "Soldering, circuit diagnostics, screen replacement, "
            "basic Python from YouTube, customer service, teaching apprentices."
        ),
        additional_information="I speak English and Twi fluently. I've taught two younger siblings phone repair.",
        country_code="GH",
        countries_config=sample_countries,
    )

    print(result["human_readable"])
    print("\n── Raw JSON ──")
    print(json.dumps(result, indent=2))
