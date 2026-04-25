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

from skills_engine import assess_skills
from risk_engine import assess_automation_risk
from opportunity_engine import match_opportunities
from report_engine import generate_report

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
    skills_profile: SkillsProfile
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
            "assess_skills": "POST /assess-skills",
            "match_opportunities": "POST /match-opportunities",
            "report": "GET /report"
        }
    }


@app.post("/assess-skills", response_model=SkillsProfile)
async def assess_skills_endpoint(request: SkillsAssessmentRequest):
    """
    Module 01 + 02: Skills Signal Engine + AI Readiness

    Takes user's self-description and returns:
    - Structured ISCO/ESCO skills profile
    - Human-readable summary
    - Automation risk assessment
    """
    country_config = load_country_config(request.country_code)
    isco_taxonomy = load_isco_taxonomy()
    esco_skills = load_esco_skills()
    frey_osborne = load_frey_osborne()

    # Module 01: Assess skills
    profile = await assess_skills(
        user_input=request.user_input,
        country_config=country_config,
        isco_taxonomy=isco_taxonomy,
        esco_skills=esco_skills
    )

    # Module 02: Assess automation risk
    profile.automation_risk = await assess_automation_risk(
        skills_profile=profile,
        country_config=country_config,
        frey_osborne=frey_osborne
    )

    return profile


@app.post("/match-opportunities", response_model=OpportunityMatchResponse)
async def match_opportunities_endpoint(request: OpportunityMatchRequest):
    """
    Module 03: Opportunity Matching

    Takes skills profile and returns ranked opportunities with:
    - Sector growth signals (visible econometric data)
    - Wage ranges (visible econometric data)
    - Skill gaps and next steps
    """
    country_config = load_country_config(request.country_code)

    opportunities = await match_opportunities(
        skills_profile=request.skills_profile,
        country_config=country_config,
        region=request.region
    )

    return OpportunityMatchResponse(
        opportunities=opportunities,
        country=country_config["country_name"],
        region=request.region
    )


@app.get("/report", response_model=ReportResponse)
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

    report = await generate_report(
        country_config=country_config,
        region=region,
        sector=sector
    )

    return report


# ============================================================================
# Run with: uvicorn main:app --reload
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
