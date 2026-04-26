"""
Canonical taxonomy for skill gaps + Claude-based classifier.

The opportunity engine generates rich, free-text `skill_gap` strings per user.
Those strings are perfect for the user-facing response but useless for
aggregation — two real users almost never produce identical strings.

This module maps each free-text gap into one of a small canonical category set
via a single batched Haiku call, so aggregated reports show stable buckets.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Optional

import anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

CANONICAL_GAPS: list[str] = [
    # Foundational education
    "Digital literacy / basic computer skills",
    "Numeracy / mathematical reasoning",
    "English or local lingua franca proficiency",
    "Formal certification or credential",
    # Specific technical / sector skills
    "Coding / software engineering",
    "Data analysis / spreadsheets",
    "Mobile device or electronics repair",
    "Solar / renewable energy installation",
    "Construction / building trades",
    "Trade apprenticeship (carpentry, welding, plumbing)",
    "Agricultural techniques / farm management",
    "Healthcare / medical technical skills",
    "Hospitality / food service skills",
    "Sector-specific technical training",
    # Business / financial
    "Financial literacy / record-keeping",
    "Business planning / entrepreneurship training",
    "Initial capital or financing",
    "Access to credit or microfinance",
    "Marketing / customer acquisition",
    "Sales technique / negotiation",
    # Workplace soft skills
    "Workplace communication and time management",
    "Leadership / supervisory experience",
    "Customer service / interpersonal skills",
    "Problem-solving / critical thinking",
    # Job-search & networks
    "CV writing / interview preparation",
    "Professional network / referrals",
    # Regulatory / safety
    "Safety, regulatory, or compliance training",
    "Business registration / legal compliance",
    # Logistical / access
    "Tools, equipment, or workspace access",
    "Transportation / mobility",
    "Mentorship / on-the-job training",
    "Other",
]

_CLASSIFIER_MODEL = "claude-haiku-4-5-20251001"

_client: Optional[anthropic.Anthropic] = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def _normalize(label: str) -> Optional[str]:
    """Snap Claude's reply to an exact CANONICAL_GAPS entry, or None if no match."""
    if not label:
        return None
    cleaned = re.sub(r'^[-•*"\'\s]+|["\'\s]+$', "", label)
    if cleaned in CANONICAL_GAPS:
        return cleaned
    lower = cleaned.lower()
    for g in CANONICAL_GAPS:
        if g.lower() == lower:
            return g
    return None


def classify_batch(texts: list[str]) -> list[Optional[str]]:
    """Classify a batch of free-text gaps in one Haiku call.

    Returns a list of the same length as ``texts``. Each element is either
    a canonical label or None (caller should fall back to the original text).
    Empty / whitespace inputs return None without an API call.
    """
    if not texts:
        return []
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return [None] * len(texts)

    # Map non-empty inputs to a compact list, remember their original positions
    indexed = [(i, t.strip()) for i, t in enumerate(texts) if t and t.strip()]
    if not indexed:
        return [None] * len(texts)

    options = "\n".join(f"- {g}" for g in CANONICAL_GAPS)
    items = "\n".join(f"{n+1}. {t}" for n, (_, t) in enumerate(indexed))

    prompt = (
        "Map each numbered skill gap below to the single best-fitting category from "
        "this allowed list:\n"
        f"{options}\n\n"
        "Skill gaps:\n"
        f"{items}\n\n"
        "Respond with ONLY a JSON array of strings — one entry per gap, in the same "
        'order. Each entry must be exactly one of the categories above (verbatim). '
        'Use "Other" when nothing fits. No prose, no markdown.'
    )

    try:
        resp = _get_client().messages.create(
            model=_CLASSIFIER_MODEL,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        raw = re.sub(r"^```[a-z]*\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        labels = json.loads(raw)
        if not isinstance(labels, list) or len(labels) != len(indexed):
            return [None] * len(texts)
    except Exception as exc:
        print(f"[gap_taxonomy] classify_batch failed: {exc}")
        return [None] * len(texts)

    out: list[Optional[str]] = [None] * len(texts)
    for (orig_idx, _), label in zip(indexed, labels):
        out[orig_idx] = _normalize(str(label))
    return out
