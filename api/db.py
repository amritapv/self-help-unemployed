"""SQLite connection + schema bootstrap for the policymaker aggregation store."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "unmapped.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    id TEXT PRIMARY KEY,
    country_code TEXT NOT NULL,
    region TEXT,
    sector_hint TEXT,
    isced_level TEXT,
    automation_risk_band TEXT,
    automation_calibrated_score REAL,
    portable_summary TEXT,
    source TEXT NOT NULL DEFAULT 'live',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    raw_profile TEXT
);

CREATE INDEX IF NOT EXISTS idx_profiles_country_region ON profiles(country_code, region);
CREATE INDEX IF NOT EXISTS idx_profiles_source ON profiles(source);

CREATE TABLE IF NOT EXISTS profile_skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    skill_name TEXT NOT NULL,
    skill_type TEXT,
    level TEXT
);

CREATE INDEX IF NOT EXISTS idx_profile_skills_profile ON profile_skills(profile_id);
CREATE INDEX IF NOT EXISTS idx_profile_skills_name ON profile_skills(skill_name);

CREATE TABLE IF NOT EXISTS profile_occupations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    isco_code TEXT NOT NULL,
    title TEXT,
    confidence TEXT
);

CREATE INDEX IF NOT EXISTS idx_profile_occupations_profile ON profile_occupations(profile_id);
CREATE INDEX IF NOT EXISTS idx_profile_occupations_isco ON profile_occupations(isco_code);

CREATE TABLE IF NOT EXISTS profile_opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    title TEXT,
    opportunity_type TEXT,
    isco_code TEXT,
    sector TEXT,
    has_skill_gap INTEGER NOT NULL DEFAULT 0,
    skill_gap_text TEXT,
    sector_growth_pct REAL
);

CREATE INDEX IF NOT EXISTS idx_profile_opportunities_profile ON profile_opportunities(profile_id);
CREATE INDEX IF NOT EXISTS idx_profile_opportunities_sector ON profile_opportunities(sector);

CREATE TABLE IF NOT EXISTS telegram_sessions (
    chat_id INTEGER PRIMARY KEY,
    messages TEXT NOT NULL DEFAULT '[]',
    collected_data TEXT,
    profile_id TEXT,
    country_code TEXT NOT NULL DEFAULT 'GH',
    language TEXT NOT NULL DEFAULT 'en',
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


@contextmanager
def connect(db_path: Path = DB_PATH):
    """Yield a sqlite3 connection with row factory + foreign keys on."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path = DB_PATH) -> None:
    """Create tables if they don't exist. Safe to call repeatedly."""
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
