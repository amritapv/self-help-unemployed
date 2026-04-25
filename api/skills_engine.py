"""
Module 01: Skills Signal Engine
Maps user input to ISCO-08/ESCO skills profile.
"""

import anthropic
import json

client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are a skills assessment engine for UNMAPPED, helping youth in {country} understand their skills.

Given a user's education, work experience, and self-described skills, create a skills profile.

IMPORTANT:
- Treat informal work and self-taught skills as VALID and valuable
- Be encouraging - focus on what they CAN do
- Use plain language they can understand

Return ONLY valid JSON in this exact format:
{{
  "matched_occupations": [
    {{"isco_code": "7421", "title": "Electronics Equipment Installer and Repairer", "confidence": 0.85}}
  ],
  "skills": [
    {{"esco_id": "S1.8.1", "skill_name": "Circuit diagnostics", "level": "intermediate", "evidence": "5 years phone repair"}}
  ],
  "education_level": {{
    "isced_level": "3",
    "description": "Upper secondary education",
    "local_equivalent": "WASSCE"
  }},
  "languages": [
    {{"language": "English", "proficiency": "fluent"}}
  ],
  "portable_summary": "A 3-4 sentence summary of their skills that they can be proud of.",
  "automation_risk": {{
    "overall_risk": "moderate",
    "calibrated_score": 0.43,
    "at_risk_tasks": ["routine diagnostics"],
    "durable_skills": ["complex repair", "customer service"],
    "adjacent_skills_for_resilience": ["solar installation", "networking"],
    "plain_language_summary": "A plain language explanation of their automation risk and what skills to build."
  }}
}}

Common ISCO codes for informal economy:
- 7421: Electronics Equipment Installer and Repairer
- 7411: Building and Related Electricians
- 5223: Shop Sales Assistants
- 7231: Motor Vehicle Mechanics
- 3512: ICT User Support Technician
- 5243: Door-to-door Sales Workers
- 2512: Software Developers
- 5241: Fashion/Clothing Sellers"""


async def assess_skills(user_input: str, country_config: dict):
    """Assess user's skills from their self-description."""

    country = country_config.get("country_name", "Ghana")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=SYSTEM_PROMPT.format(country=country),
        messages=[
            {"role": "user", "content": user_input}
        ]
    )

    # Parse the JSON response
    response_text = response.content[0].text

    # Try to extract JSON if wrapped in markdown
    if "```json" in response_text:
        import re
        match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if match:
            response_text = match.group(1)
    elif "```" in response_text:
        import re
        match = re.search(r'```\s*(.*?)\s*```', response_text, re.DOTALL)
        if match:
            response_text = match.group(1)

    profile_data = json.loads(response_text)

    # Import here to avoid circular dependency
    from main import SkillsProfile, MatchedOccupation, Skill, Language, EducationLevel, AutomationRisk

    return SkillsProfile(
        matched_occupations=[MatchedOccupation(**occ) for occ in profile_data["matched_occupations"]],
        skills=[Skill(**s) for s in profile_data["skills"]],
        education_level=EducationLevel(**profile_data["education_level"]),
        languages=[Language(**lang) for lang in profile_data["languages"]],
        portable_summary=profile_data["portable_summary"],
        automation_risk=AutomationRisk(**profile_data["automation_risk"])
    )
