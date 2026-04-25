# UNMAPPED — Product Requirements Document

**Version:** 1.0 (Hackathon MVP)
**Date:** April 25, 2026
**Team:** Amrita, Nimisha, Rufo
**Build window:** ~8 hours (target 6-7pm), hard deadline tomorrow morning

---

## 1. Problem

Hundreds of millions of young people in LMICs have real skills — informal, unverified, uncredentialed — that are invisible to employers, training programs, and labor market systems. Simultaneously, automation is redrawing which skills are durable, and youth have no tools to navigate this. No single infrastructure layer connects skills assessment, displacement risk, and opportunity matching for this population.

UNMAPPED is an API layer that any government, NGO, or training provider can plug into. The web chat interface is one example client consuming this infrastructure.

---

## 2. User Personas

**Amara (primary)** — 22, outside Accra, secondary school cert, runs a phone repair business, self-taught coder. Speaks three languages. Needs plain-language outputs she can understand and act on from a mobile device.

**Program Officer / Policymaker (secondary)** — NGO or government official managing youth employment programs. Needs aggregate signals: where are skills gaps, which sectors are growing, how many youth are at automation risk in their region.

---

## 3. What We're Building

Three modules, one API:

| Module | Challenge Req | What It Does |
|--------|--------------|--------------|
| **01 — Skills Signal Engine** | Required | Takes education + informal experience + competencies → produces a portable ISCO/ESCO skills profile that Amara can read and own |
| **02 — AI Readiness & Displacement Risk** | Bonus (differentiator) | Flags automation exposure per skill/occupation, identifies durable skills, suggests adjacent skills for resilience |
| **03 — Opportunity Matching + Policymaker API** | Required | Matches skills profile to real opportunities using econometric signals. Dual interface: youth user sees opportunities, policymaker hits an API for aggregate data |

Module 02 is lightweight once Module 01 exists — it's a lookup against Frey-Osborne automation scores + a calibration factor + an LLM call to contextualize. Including all three differentiates us from teams that only built two.

---

## 4. Architecture

```
┌──────────────────────────────────────────────────┐
│                    CLIENTS                        │
│  ┌──────────────────┐   ┌─────────────────────┐  │
│  │  Web Chat UI     │   │  Policymaker        │  │
│  │  (primary demo)  │   │  (calls /report)    │  │
│  └────────┬─────────┘   └──────────┬──────────┘  │
└───────────┼────────────────────────┼─────────────┘
            │                        │
            ▼                        ▼
┌──────────────────────────────────────────────────┐
│               CORE API (FastAPI)                  │
│                                                   │
│  POST /assess-skills                              │
│    → User input (text)                            │
│    → Returns: structured ISCO/ESCO skills profile │
│    → Returns: human-readable summary              │
│    → Returns: automation risk assessment (Mod 02) │
│                                                   │
│  POST /match-opportunities                        │
│    → Skills profile + country code                │
│    → Returns: ranked opportunities with 2+        │
│      visible econometric signals                  │
│                                                   │
│  GET /report?country=GH&sector=X&region=Y         │
│    → Returns: aggregated JSON for policymakers    │
│    → Skills gaps, automation risk distribution,   │
│      sector signals, demographic breakdowns       │
│                                                   │
└───────────────────┬──────────────────────────────┘
                    │
           ┌────────┴────────┐
           ▼                 ▼
   ┌─────────────┐   ┌──────────────┐
   │ Claude API  │   │ Data Layer   │
   │ (Sonnet)    │   │ countries.   │
   │             │   │ json +       │
   │ - skills    │   │ frey_osborne │
   │   mapping   │   │ .json +      │
   │ - risk      │   │ isco/esco    │
   │   context   │   │ taxonomies   │
   │ - matching  │   │              │
   └─────────────┘   └──────────────┘
```

All three modules are API endpoints on a single FastAPI backend. The web chat UI is a React client that calls these endpoints. The policymaker API is the same backend, different endpoint. In production, this same API would serve a Telegram, WhatsApp, or SMS client.

---

## 5. Tech Stack

| Layer | Tool | Rationale |
|-------|------|-----------|
| Core API | Python + FastAPI | Fast to build, async-friendly, auto-generated docs at /docs |
| LLM | Claude API (Sonnet) | Skills mapping, risk contextualization, opportunity matching |
| Web frontend | React + Vite + Tailwind | Chat UI + results rendering, mobile-first |
| Data | Pre-processed JSON files | No database needed for hackathon |
| Hosting | Localhost | Don't waste time on deployment |

**Total cost:** ~$5-10 in API calls for the full hackathon.

---

## 6. Country Config

All country-specific parameters live in a single `countries.json` file, keyed by country code. This is how we prove "protocol, not product."

```json
{
  "GH": {
    "country_name": "Ghana",
    "context": "Sub-Saharan Africa, urban informal economy",
    "language": { "primary": "en", "local": ["tw", "ee", "ha"] },
    "currency": "GHS",
    "education_taxonomy": [
      {"local": "BECE",  "isced": "2", "label": "Lower secondary"},
      {"local": "WASSCE","isced": "3", "label": "Upper secondary"},
      {"local": "HND",   "isced": "5", "label": "Short-cycle tertiary"},
      {"local": "Bachelor's", "isced": "6", "label": "Bachelor's"}
    ],
    "automation_calibration": {
      "infrastructure_factor": 0.6,
      "notes": "Lower automation adoption — Frey-Osborne scores discounted 40%"
    },
    "opportunity_types": [
      "formal_employment", "self_employment", "gig",
      "apprenticeship", "training_pathway"
    ],
    "econometric": {
      "sector_growth": {"ict": 0.14, "agriculture": 0.03,
                        "manufacturing": 0.06, "services": 0.09},
      "wage_data": {"isco_7421": {"min": 1800, "max": 2400}},
      "youth_unemployment": 0.128,
      "informality_rate": 0.89
    }
  },
  "IN": { ... }
}
```

**Configurable without code changes:** labor market data, education taxonomy, language, automation calibration, opportunity types.

**Demo plan:** Show Ghana config, then swap to India — different education levels (CBSE/ICSE), different sectors (agriculture-heavy), different automation calibration. Same code, different key.

---

## 7. Module Specifications

### Module 01: Skills Signal Engine

**User flow:**
1. User opens the web chat
2. Bot asks conversational questions: education level, work experience (formal and informal), languages, self-taught skills, tools/technologies
3. User responds via text
4. Backend sends collected input to Claude API with ISCO-08/ESCO taxonomy + country education taxonomy as context
5. Claude returns structured skills profile as JSON
6. System renders human-readable profile back to user in the chat

**Claude API prompt structure:**
```
System: You are a skills assessment engine. Given a user's
self-described education, work experience, and competencies,
map them to ISCO-08 occupational classification and ESCO
skills taxonomy.

Return JSON with:
- matched_occupations: [{isco_code, title, confidence}]
- skills: [{esco_id, skill_name, level, evidence}]
- education_level: {isced_level, description}
- languages: [{language, proficiency}]
- portable_summary: 3-4 sentence plain-language summary

User is in {country}. Education taxonomy: {education_taxonomy}.
Prioritize informal and self-taught skills as valid signals.
```

**What Amara sees (human-readable output):**
```
Your Skills Profile

You have strong hands-on technical skills in electronics
repair, with 5 years of demonstrated experience. You've also
built foundational digital skills including basic programming
and online troubleshooting.

Your skills map to:
  Electronics Equipment Installer & Repairer (ISCO 7421)
  ICT User Support Technician (ISCO 3512)

Technical Skills: Circuit diagnostics, soldering, component
  replacement, basic Python
Languages: English (fluent), Twi (native), Ga (conversational)
Education: WASSCE (Upper Secondary — ISCED Level 3)

This profile is portable — it follows international standards
used across 90+ countries.
```

**Required outputs:**
- Structured JSON (for API consumers and downstream modules)
- Human-readable summary (for the user, in plain language)
- ISCO-08 codes + ESCO skill IDs (for portability)

---

### Module 02: AI Readiness & Displacement Risk

**How it works:**
1. Takes the skills profile from Module 01
2. Looks up matched ISCO occupations against Frey-Osborne automation probability dataset
3. Applies the country's `infrastructure_factor` to calibrate for local context
4. Sends profile + calibrated automation data to Claude API for contextual interpretation
5. Returns: risk flags, durable skills, 2-3 adjacent skills for resilience

**Calibration logic:**
```python
raw_score = frey_osborne[isco_code]       # e.g. 0.72
infra_factor = config["automation_calibration"]["infrastructure_factor"]  # e.g. 0.6
calibrated_score = raw_score * infra_factor  # 0.43
```

The infrastructure factor discounts automation probability for contexts where capital investment in automation technology is lower. This is a simplification — we'll say so explicitly.

**What Amara sees:**

All outputs in plain, accessible language. Numbers are always wrapped in meaning — not "automation probability: 0.43" but "about 4 in 10 of the tasks in your type of work could be done by machines in the future, though this is less likely in Ghana right now."

```
Your AI Readiness Check

Your work in phone repair has moderate automation risk
in the Ghanaian context.

At risk: Routine diagnostic checks, standard screen
replacements — these tasks are increasingly automated
in some markets.

Durable: Complex circuit repair, customer problem
diagnosis, teaching others — these require judgment
and human interaction that machines can't replace.

Skills to build for resilience:
  - Data recovery & software troubleshooting
    (adjacent to what you know, high demand)
  - Solar panel installation & maintenance
    (growing sector, very low automation risk)
  - Basic networking/WiFi setup
    (combines your electronics + digital skills)

Your automation risk is lower in Ghana than in
high-income countries because the economics of
deploying repair automation don't yet favor it here.
Building adjacent skills now puts you ahead.
```

---

### Module 03: Opportunity Matching + Policymaker API

This module has a **dual interface** as required by the brief: one for the youth user (opportunities), one for the policymaker (aggregate data).

#### Youth-Facing: Opportunity Matching

**Two required econometric signals (visible to user, not buried):**

| Signal | Source | What Amara Sees |
|--------|--------|----------------|
| Sector employment growth | ILOSTAT | "Mobile repair jobs in Accra have grown 12% in the last 2 years" |
| Wage floor / expected earnings | World Bank WDI + ILOSTAT | "People doing this work in Accra typically earn GHS 1,800–2,400 per month" |

Signals are always expressed in plain language with local context. Not "sector CAGR: 12%."

**Matching logic:**
1. Takes skills profile (Module 01) + risk assessment (Module 02) + country config
2. Loads pre-processed econometric data for user's country
3. Claude API call: given profile, risk data, and econometric context, rank 3-5 realistic, reachable opportunities
4. Each opportunity shows: title, type, why it fits, sector growth signal, wage range, gap to fill, concrete next step

**What Amara sees:**
```
Opportunities For You
Based on your skills and labor market data for Greater Accra:

1. Mobile Device Technician — TechServ Ghana
   This sector has grown 14% per year recently
   Expected earnings: GHS 1,800 – 2,400/month
   Strong fit for your repair skills
   Gap: Formal certification (3-month program at NVTI)
   Next step: Register at nvti.gov.gh for Q3 intake

2. Solar Installation Technician — self-employment
   Renewable energy has grown 22% per year recently
   Expected earnings: GHS 2,000 – 3,200/month
   Your electronics diagnostics transfer directly
   Gap: 2-week solar panel training (free via
   Energy Commission)

3. IT Support — entry-level gig/contract
   Business services have grown 9% per year recently
   Expected earnings: GHS 1,200 – 1,600/month
   Your coding and troubleshooting skills qualify
   you now — no additional training needed
```

Matching is honest and grounded. If self-employment is the most realistic path, we say so. We don't match aspirationally.

#### Policymaker-Facing: Aggregate API

**No frontend UI for MVP.** The `/report` endpoint returns JSON:

```
GET /report?country=GH&region=greater-accra&sector=all
```

Returns:
```json
{
  "report_meta": {
    "country": "Ghana",
    "region": "Greater Accra",
    "profiles_assessed": 1247,
    "report_date": "2026-04-25"
  },
  "skills_distribution": {
    "top_skills": [
      {"skill": "Electronics repair", "count": 342, "pct": 0.27},
      {"skill": "Sales & customer service", "count": 298, "pct": 0.24}
    ],
    "education_levels": {
      "ISCED_2": 0.41, "ISCED_3": 0.38, "ISCED_5_plus": 0.21
    }
  },
  "automation_exposure": {
    "high_risk": {"pct": 0.18,
      "top_occupations": ["data entry", "basic assembly"]},
    "moderate_risk": {"pct": 0.45,
      "top_occupations": ["retail sales", "routine repair"]},
    "low_risk": {"pct": 0.37,
      "top_occupations": ["healthcare support", "teaching"]}
  },
  "opportunity_gaps": {
    "highest_growth_sectors": ["ICT services", "renewable energy"],
    "biggest_skill_gaps": ["digital literacy", "formal certification"],
    "recommended_interventions": [
      "Expand NVTI certification access — 27% of profiled youth are one credential away from formal employment",
      "Solar installation training — high growth sector with low entry barrier"
    ]
  },
  "econometric_signals": {
    "youth_unemployment": 0.128,
    "informality_rate": 0.89,
    "sector_growth": {"ict": 0.14, "agriculture": 0.03}
  }
}
```

V2 adds a dashboard UI for this data.

---

## 8. Data Pipeline

**Pre-processed before/at start of hackathon (do this FIRST — it unblocks everything):**

| Dataset | Source | What We Extract |
|---------|--------|----------------|
| Frey-Osborne automation scores | Published dataset (CSV) | Automation probability per occupation, keyed by ISCO code |
| ILOSTAT employment by sector | ilostat.ilo.org bulk download | Sector employment levels, growth rates for Ghana + India |
| World Bank WDI | databank.worldbank.org | Wage indices, youth unemployment, education returns |
| ISCO-08 taxonomy | ILO | Occupation codes, titles, task descriptions |
| ESCO skills taxonomy | ec.europa.eu/esco | Skills IDs, names, relationships to ISCO |

**What "pre-process" means:**
- Download CSVs from the sources above
- Filter to demo countries (Ghana + India)
- Merge all country-specific data into `countries.json` keyed by country code
- Frey-Osborne and ISCO/ESCO are global, so they stay as separate files

**Data files:**
```
data/
├── countries.json         # Country configs + econometric data
├── frey_osborne.json      # Automation scores by ISCO code
├── isco08_taxonomy.json   # Occupation codes + descriptions
└── esco_skills.json       # Skills taxonomy
```

---

## 9. Sprint Plan (8 Hours, 3 People)

### Hour 0–1: Setup & Data

| Who | Task |
|-----|------|
| **Amrita** | FastAPI project skeleton, API route stubs, Claude API integration |
| **Nimisha** | Download + pre-process datasets into JSON. Build `countries.json` for Ghana + India |
| **Rufo** | React + Vite + Tailwind project. Scaffold chat UI layout (message list, input bar, results area) |

### Hour 1–3: Module 01 + 02

| Who | Task |
|-----|------|
| **Amrita** | Build `/assess-skills`: user text → Claude API call with ISCO/ESCO context → structured profile + human-readable summary. Add Frey-Osborne lookup + calibration logic (Module 02) |
| **Nimisha** | Finish data processing. Build data-loading functions (load country config, return econometric data for country+sector). Start `/match-opportunities` logic |
| **Rufo** | Build chat flow: welcome → conversational questions → collect answers → POST to `/assess-skills` → render skills profile card + automation risk display |

### Hour 3–5: Module 03 + Integration

| Who | Task |
|-----|------|
| **Amrita** | Build `/match-opportunities`: skills profile + country config + econometric data → Claude API → ranked opportunities with visible signals. Build `/report` endpoint |
| **Nimisha** | End-to-end testing. Fix data edge cases. Help with opportunity matching prompt tuning |
| **Rufo** | Build opportunity results view with prominent econometric signals. Country selector in UI. Mobile responsiveness |

### Hour 5–6.5: Country Switch + Polish

| Who | Task |
|-----|------|
| **Amrita** | Test full Ghana flow end-to-end. Swap to India config, verify reconfiguration works |
| **Nimisha** | Test India flow. Fix edge cases. Prepare sample policymaker API call + response |
| **Rufo** | Polish UI: skills profile card, risk display, opportunity cards. Ensure plain language throughout |

### Hour 6.5–8: Demo Prep

| Who | Task |
|-----|------|
| **All** | Dry-run demo 2x. Prepare talking points. Record backup video. Write "what we'd build next" notes |

---

## 10. Demo Script (5–7 Minutes)

1. **The problem** (30s) — "Meet Amara. She has skills. The formal economy doesn't know she exists."

2. **Architecture** (45s) — Show the API structure. "We built infrastructure, not an app. Three endpoints. Any client — web, WhatsApp, SMS — can connect."

3. **Live demo — Amara's flow** (2.5min) — Walk through the chat. She describes her background. System returns her skills profile (Module 01), shows automation risk in plain language (Module 02), surfaces opportunities with real wage and growth data (Module 03). Point out the two visible econometric signals.

4. **Country switch** (1min) — Swap from Ghana to India. Show education taxonomy changes, sector rebalancing, automation recalibration. Same code, different config.

5. **Policymaker API** (45s) — Hit `/report` endpoint live. Show aggregated skills gaps, automation exposure distribution, recommended interventions.

6. **What's next** (30s) — Telegram/WhatsApp client, audio input via Whisper, live data feeds from ILOSTAT/WDI, Wittgenstein Centre education projections for forward-looking risk, multilingual UI translation.

---

## 11. Judging Criteria Alignment

| Criterion | How We Hit It |
|-----------|--------------|
| "Show the data — 2+ econometric signals visible" | Sector growth rate + wage floor on every opportunity card, in plain language |
| "Design for constraint — low bandwidth, shared devices" | Mobile-first chat UI, text-based flow, no heavy assets |
| "Demonstrate localizability with real evidence" | Live country config swap Ghana → India, no code changes |
| "Be honest about limits" | Frey-Osborne calibration noted as simplification. Pre-processed vs. live data stated. Known limitations listed |
| "Infrastructure, not just an app" | Clean API with documented endpoints. Web UI is one example client. Policymaker endpoint separate from user flow |
| "Profile must be portable, explainable to non-expert" | ISCO/ESCO codes for portability, plain-language summary for user |
| "Dual interface for Module 03" | Youth view (chat opportunities) + policymaker view (aggregate JSON API) |

---

## 12. Known Limitations (Say These Out Loud)

- Automation risk calibration uses a single infrastructure discount factor per country — a more nuanced model would account for sector-specific automation adoption curves
- Econometric data is pre-processed snapshots, not live feeds — production system would pull from ILOSTAT/WDI APIs on a schedule
- Skills mapping relies on LLM inference, not verified credentials — production adds a verification/endorsement layer
- Aggregation for policymaker reports uses demo data, not a real user base
- Wittgenstein Centre education projections (mentioned in brief) not yet incorporated — clear next step for forward-looking risk
- No multilingual UI translation in MVP — architecture supports it via Claude translation layer, V2 feature

---

## 13. Out of Scope (MVP)

- Live multilingual UI translation (roadmap — mention in demo)
- Audio input (roadmap — mention Whisper integration path in demo)
- Real-time API calls to external datasets (pre-fetched static JSON for demo stability)
- User accounts / auth
- Policymaker dashboard UI (V2)
- Telegram / WhatsApp client (roadmap — same API, different client wrapper)

---

## 14. Success Criteria

- [ ] Amara completes skills intake via chat and receives a human-readable profile
- [ ] Profile includes automation risk assessment in plain language
- [ ] At least 2 real econometric signals visible on screen in plain language
- [ ] Amara sees 3+ matched opportunities with wage and growth data
- [ ] Judges see a live country switch (Ghana → India) with no code changes
- [ ] Policymaker API call returns aggregate JSON

---

## 15. File Structure

```
unmapped/
├── api/
│   ├── main.py                # FastAPI app, route definitions
│   ├── skills_engine.py       # Module 01: skills assessment
│   ├── risk_engine.py         # Module 02: automation risk
│   ├── opportunity_engine.py  # Module 03: opportunity matching
│   └── report_engine.py       # Policymaker aggregation
├── data/
│   ├── countries.json         # All country configs + econometric data
│   ├── frey_osborne.json      # Automation scores by ISCO code
│   ├── isco08_taxonomy.json   # Occupation codes + descriptions
│   └── esco_skills.json       # Skills taxonomy
├── web/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── ChatView.jsx       # Chat-style input flow
│   │   ├── ProfileCard.jsx    # Skills profile display
│   │   ├── RiskDisplay.jsx    # Automation risk display
│   │   └── OpportunityList.jsx # Opportunity cards w/ signals
│   └── ...
└── README.md
```
