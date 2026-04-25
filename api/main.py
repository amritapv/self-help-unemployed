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

class SkillsAssessmentRequest(BaseModel):
    """Input for skills assessment - user's self-description"""
    education: str # no specific format, processed text from chat conversation
    experience: str
    skills_self_reported: str
    additional_info: str
    country_code: str = "GH"  # Default to Ghana


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


class ChatResponse(BaseModel):
    message: str
    collected_data: Optional[dict] = None  # Filled when enough info gathered
    ready_for_assessment: bool = False


# ============================================================================
# Claude Client
# ============================================================================

claude_client = anthropic.Anthropic()

CHAT_SYSTEM_PROMPT = """You are a skills assessment assistant for UNMAPPED in {country}.

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
            "report": "GET /report"
        }
    }


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
        system=CHAT_SYSTEM_PROMPT.format(country=country_config.get("country_name", "Ghana")),
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
    )

    return result


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
        region=request.region
    )

    return {
        "opportunities": result.get("opportunities", []),
        "country": country_config["country_name"],
        "region": request.region,
        "note": result.get("note"),
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

    # TODO: Implement actual aggregation from stored profiles
    # For now, return placeholder structure
    return {
        "report_meta": {
            "country": country_config.get("country_name", country),
            "region": region,
            "sector": sector,
            "profiles_assessed": 0,
            "report_date": "2026-04-25"
        },
        "skills_distribution": {
            "top_skills": [],
            "education_levels": {}
        },
        "automation_exposure": {
            "high_risk": {"pct": 0, "top_occupations": []},
            "moderate_risk": {"pct": 0, "top_occupations": []},
            "low_risk": {"pct": 0, "top_occupations": []}
        },
        "opportunity_gaps": {
            "highest_growth_sectors": [],
            "biggest_skill_gaps": [],
            "recommended_interventions": []
        },
        "econometric_signals": country_config.get("econometric", {})
    }


# ============================================================================
# Run with: uvicorn main:app --reload
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
