from __future__ import annotations

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    card_bin TEXT NOT NULL,
    card_fingerprint TEXT NOT NULL,
    amount INTEGER NOT NULL,
    currency TEXT NOT NULL DEFAULT 'usd',
    customer_ip TEXT,
    customer_email TEXT,
    customer_id TEXT,
    risk_score REAL NOT NULL,
    decision TEXT NOT NULL,
    signals TEXT DEFAULT '[]',
    rules_triggered TEXT DEFAULT '[]',
    stripe_payment_intent_id TEXT,
    metadata TEXT DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rules (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    field TEXT NOT NULL,
    operator TEXT NOT NULL,
    value TEXT NOT NULL,
    action TEXT NOT NULL,
    priority INTEGER DEFAULT 0,
    enabled INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bin_cache (
    bin TEXT PRIMARY KEY,
    issuer TEXT,
    country TEXT,
    card_type TEXT,
    is_prepaid INTEGER DEFAULT 0,
    fetched_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bin_risk_stats (
    bin TEXT PRIMARY KEY,
    total_screens INTEGER DEFAULT 0,
    total_blocks INTEGER DEFAULT 0,
    total_disputes INTEGER DEFAULT 0,
    risk_ratio REAL DEFAULT 0.0,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stripe_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    payment_intent_id TEXT,
    charge_id TEXT,
    dispute_id TEXT,
    amount INTEGER,
    reason TEXT,
    payload TEXT,
    processed_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_txn_fingerprint ON transactions(card_fingerprint);
CREATE INDEX IF NOT EXISTS idx_txn_ip ON transactions(customer_ip);
CREATE INDEX IF NOT EXISTS idx_txn_created ON transactions(created_at);
CREATE INDEX IF NOT EXISTS idx_txn_decision ON transactions(decision);
CREATE INDEX IF NOT EXISTS idx_events_pi ON stripe_events(payment_intent_id);
CREATE INDEX IF NOT EXISTS idx_bin_risk ON bin_risk_stats(risk_ratio);
"""


async def init_db(db_path: str):
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(SCHEMA)
        await db.commit()
