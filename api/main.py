"""
UNMAPPED Core API
FastAPI backend for skills assessment, automation risk, and opportunity matching.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
from pathlib import Path
import anthropic

from api.skills_engine import assess_skills
from api.risk_engine import assess_automation_risk
from api.opportunity_engine import match_opportunities
from api.report_engine import generate_report
from api.gap_taxonomy import classify_batch as classify_gaps
from api import repository

app = FastAPI(
    title="UNMAPPED API",
    description="Skills assessment, automation risk, and opportunity matching for youth in LMICs",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data directory
DATA_DIR = Path(__file__).parent.parent / "data"


# ============================================================================
# Pydantic Models
# ============================================================================

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "es": "Spanish",
    "ar": "Arabic",
    "fr": "French",
}


def _language_name(code: str) -> str:
    """Map a language code to its English name. Falls back to English silently."""
    return LANGUAGE_NAMES.get((code or "en").lower(), "English")


class SkillsAssessmentRequest(BaseModel):
    """Input for skills assessment - user's self-description"""
    education: str # no specific format, processed text from chat conversation
    experience: str
    skills_self_reported: str
    additional_info: str
    country_code: str = "GH"  # Default to Ghana
    language: str = "en"


class MatchedOccupation(BaseModel):
    isco_code: str
    title: str
    confidence: float


class Skill(BaseModel):
    esco_id: str
    skill_name: str
    level: str  # beginner, intermediate, advanced
    evidence: str  # What the user said that maps to this skill


class Language(BaseModel):
    language: str
    proficiency: str  # native, fluent, conversational, basic


class EducationLevel(BaseModel):
    isced_level: str
    description: str
    local_equivalent: Optional[str] = None


class AutomationRisk(BaseModel):
    overall_risk: str  # low, moderate, high
    calibrated_score: float
    at_risk_tasks: list[str]
    durable_skills: list[str]
    adjacent_skills_for_resilience: list[str]
    plain_language_summary: str


class SkillsProfile(BaseModel):
    """Output from Module 01 + 02"""
    matched_occupations: list[MatchedOccupation]
    skills: list[Skill]
    education_level: EducationLevel
    languages: list[Language]
    portable_summary: str  # Plain language for Amara
    automation_risk: AutomationRisk  # Module 02 integrated


class OpportunityMatchRequest(BaseModel):
    """Input for opportunity matching"""
    # skills_profile is the raw dict returned by /assess-skills — do not enforce
    # the legacy SkillsProfile schema here, the engine output doesn't match it.
    skills_profile: dict
    country_code: str = "GH"
    region: Optional[str] = None
    language: str = "en"


class Opportunity(BaseModel):
    title: str
    opportunity_type: str  # formal_employment, self_employment, gig, apprenticeship, training_pathway
    employer_or_path: str
    sector_growth_signal: str  # Plain language: "This sector has grown 14% per year recently"
    wage_range: str  # Plain language: "Expected earnings: GHS 1,800 – 2,400/month"
    fit_explanation: str
    skill_gap: Optional[str] = None
    next_step: str


class OpportunityMatchResponse(BaseModel):
    opportunities: list[Opportunity]
    country: str
    region: Optional[str] = None


class ReportResponse(BaseModel):
    """Policymaker aggregate report"""
    report_meta: dict
    skills_distribution: dict
    automation_exposure: dict
    opportunity_gaps: dict
    econometric_signals: dict


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    country_code: str = "GH"
    language: str = "en"


class ChatResponse(BaseModel):
    message: str
    collected_data: Optional[dict] = None  # Filled when enough info gathered
    ready_for_assessment: bool = False


# ============================================================================
# Claude Client
# ============================================================================

claude_client = anthropic.Anthropic()

CHAT_SYSTEM_PROMPT = """You are a skills assessment assistant for UNMAPPED in {country}.

Respond in {language_name}. The user is using a {language_name}-speaking version of UNMAPPED.

Gather info about: EDUCATION, EXPERIENCE, SKILLS, and LANGUAGES/OTHER.

RULES:
- Keep questions to ONE short sentence
- Ask only ONE question at a time
- You have MAX 10 questions total - be efficient
- Informal work and self-taught skills count
- After enough info (or 10 questions), wrap up

When ready, end with:
[READY_FOR_ASSESSMENT]

And include:
```json
{{
  "education": "their education summary",
  "experience": "their work experience",
  "skills_self_reported": "their skills",
  "additional_info": "languages and other info"
}}
```"""


# ============================================================================
# Helper Functions
# ============================================================================

def load_country_config(country_code: str) -> dict:
    """Load country configuration from countries.json"""
    countries_path = DATA_DIR / "countries.json"
    with open(countries_path) as f:
        countries = json.load(f)

    if country_code not in countries:
        raise HTTPException(status_code=400, detail=f"Country code {country_code} not supported")

    return countries[country_code]


def load_frey_osborne() -> dict:
    """Load Frey-Osborne automation scores"""
    path = DATA_DIR / "frey_osborne.json"
    with open(path) as f:
        return json.load(f)


def load_isco_taxonomy() -> dict:
    """Load ISCO-08 occupation taxonomy"""
    path = DATA_DIR / "isco08_taxonomy.json"
    with open(path) as f:
        return json.load(f)


def load_esco_skills() -> dict:
    """Load ESCO skills taxonomy"""
    path = DATA_DIR / "esco_skills.json"
    with open(path) as f:
        return json.load(f)


# ============================================================================
# API Routes
# ============================================================================

@app.get("/")
async def root():
    """Health check and API info"""
    return {
        "name": "UNMAPPED API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "chat": "POST /chat",
            "assess_skills": "POST /assess-skills",
            "match_opportunities": "POST /match-opportunities",
            "report": "GET /report",
            "meta_countries": "GET /meta/countries"
        }
    }


@app.get("/meta/countries")
async def meta_countries():
    """Lightweight metadata for UI dropdowns: country -> regions + sector list."""
    countries_path = DATA_DIR / "countries.json"
    with open(countries_path) as f:
        countries = json.load(f)

    out = []
    for code, cfg in countries.items():
        if code.startswith("_"):
            continue
        out.append({
            "code": code,
            "name": cfg.get("country_name", code),
            "regions": [
                {"code": r.get("code"), "name": r.get("name")}
                for r in cfg.get("regions", [])
            ],
            "sectors": list((cfg.get("sectors") or {}).keys()),
        })
    return {"countries": out}


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Interactive chat endpoint powered by Claude.
    Gathers education, experience, skills, and additional info through conversation.
    """
    try:
        country_config = load_country_config(request.country_code)
    except:
        country_config = {"country_name": "Ghana"}

    # Convert messages to Claude format
    claude_messages = [{"role": m.role, "content": m.content} for m in request.messages]

    response = claude_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        system=CHAT_SYSTEM_PROMPT.format(
            country=country_config.get("country_name", "Ghana"),
            language_name=_language_name(request.language),
        ),
        messages=claude_messages
    )

    assistant_message = response.content[0].text

    # Check if ready for assessment
    ready = "[READY_FOR_ASSESSMENT]" in assistant_message
    collected_data = None

    if ready:
        # Extract JSON from response
        import re
        json_match = re.search(r'```json\s*(.*?)\s*```', assistant_message, re.DOTALL)
        if json_match:
            try:
                collected_data = json.loads(json_match.group(1))
            except:
                pass
        # Clean up the message
        assistant_message = assistant_message.replace("[READY_FOR_ASSESSMENT]", "").strip()
        assistant_message = re.sub(r'```json\s*.*?\s*```', '', assistant_message, flags=re.DOTALL).strip()

    return ChatResponse(
        message=assistant_message,
        collected_data=collected_data,
        ready_for_assessment=ready
    )


@app.post("/assess-skills")
async def assess_skills_endpoint(request: SkillsAssessmentRequest):
    """
    Module 01 + 02: Skills Signal Engine + AI Readiness

    Takes user's self-description and returns:
    - Structured ISCO/ESCO skills profile
    - Human-readable summary
    - Automation risk assessment
    """
    # skills_engine expects countries_config as {country_code: config}
    try:
        country_config = load_country_config(request.country_code)
        countries_config = {request.country_code: country_config}
    except:
        countries_config = {}

    result = assess_skills(
        education=request.education,
        experience=request.experience,
        skills=request.skills_self_reported,
        additional_information=request.additional_info,
        country_code=request.country_code,
        countries_config=countries_config,
        language=request.language,
    )

    # Compute automation risk inline (deterministic, no Claude call) so we can
    # persist a complete record and return it to the frontend.
    automation_risk = {}
    if countries_config:
        try:
            frey_osborne = load_frey_osborne()
            automation_risk = assess_automation_risk(result, country_config, frey_osborne)
        except Exception as exc:
            print(f"[assess-skills] risk_engine failed: {exc}")

    # Sector hint from primary matched occupation, if available
    sector_hint = None
    occupations = result.get("matched_occupations") or []
    if occupations and countries_config:
        primary_isco = str(occupations[0].get("isco_code", "")).strip()
        wage_entry = (country_config.get("wage_data") or {}).get(primary_isco) or {}
        sector_hint = wage_entry.get("sector")

    profile_id = None
    try:
        profile_id = repository.insert_profile(
            skills_profile=result,
            automation_risk=automation_risk,
            opportunities=[],
            country_code=request.country_code,
            sector_hint=sector_hint,
            source="live",
        )
    except Exception as exc:
        # Persistence failure shouldn't break the user-facing response
        print(f"[assess-skills] persistence failed: {exc}")

    return {**result, "profile_id": profile_id, "automation_risk": automation_risk}


@app.post("/match-opportunities")
async def match_opportunities_endpoint(request: OpportunityMatchRequest):
    """
    Module 03: Opportunity Matching

    Takes skills profile and returns ranked opportunities with:
    - Sector growth signals (visible econometric data)
    - Wage ranges (visible econometric data)
    - Skill gaps and next steps
    """
    country_config = load_country_config(request.country_code)
    frey_osborne = load_frey_osborne()

    # skills_profile is already a dict (loosened the request schema above).
    result = match_opportunities(
        skills_profile=request.skills_profile,
        country_config=country_config,
        frey_osborne=frey_osborne,
        region=request.region,
        language=request.language,
    )

    opportunities = result.get("opportunities", [])

    # Canonicalize skill_gap for persistence only (the response payload still
    # carries Claude's rich, user-specific phrasing).
    gap_texts = [(opp.get("skill_gap") or "") for opp in opportunities]
    canonical_labels = classify_gaps(gap_texts) if any(gap_texts) else [None] * len(opportunities)
    persisted_opps = []
    for opp, label in zip(opportunities, canonical_labels):
        copy = dict(opp)
        if label and copy.get("skill_gap"):
            copy["skill_gap"] = label
        persisted_opps.append(copy)

    # Persist: attach to existing profile if profile_id was carried through,
    # otherwise insert a fresh standalone record (covers direct API callers).
    profile_id = request.skills_profile.get("profile_id")
    try:
        if profile_id and repository.attach_opportunities(profile_id, persisted_opps):
            pass
        else:
            risk = assess_automation_risk(request.skills_profile, country_config, frey_osborne)
            occupations = request.skills_profile.get("matched_occupations") or []
            sector_hint = None
            if occupations:
                primary_isco = str(occupations[0].get("isco_code", "")).strip()
                wage_entry = (country_config.get("wage_data") or {}).get(primary_isco) or {}
                sector_hint = wage_entry.get("sector")
            profile_id = repository.insert_profile(
                skills_profile=request.skills_profile,
                automation_risk=risk,
                opportunities=persisted_opps,
                country_code=request.country_code,
                region=request.region,
                sector_hint=sector_hint,
                source="live",
            )
    except Exception as exc:
        print(f"[match-opportunities] persistence failed: {exc}")

    return {
        "opportunities": opportunities,
        "country": country_config["country_name"],
        "region": request.region,
        "note": result.get("note"),
        "profile_id": profile_id,
    }


@app.get("/report")
async def report_endpoint(
    country: str = "GH",
    region: Optional[str] = None,
    sector: Optional[str] = None
):
    """
    Policymaker API: Aggregate Report

    Returns aggregated data for program officers:
    - Skills distribution
    - Automation exposure by risk level
    - Opportunity gaps and recommended interventions
    - Econometric signals
    """
    country_config = load_country_config(country)
    return generate_report(country_config, region=region, sector=sector)


# ============================================================================
# Run with: uvicorn main:app --reload
# ============================================================================

if __name__ == "__main__":
    # Run from the repo root with: python -m uvicorn api.main:app --reload
    # The string form below also allows `python -m api.main` to work.
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000)
