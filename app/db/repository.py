from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Optional

import aiosqlite

from app.models.enums import RiskDecision


class Repository:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    # --- Transactions ---

    async def save_transaction(
        self, id: str, card_bin: str, card_fingerprint: str, amount: int,
        currency: str, customer_ip: str, customer_email: Optional[str],
        customer_id: Optional[str], risk_score: float, decision: str,
        signals: list, rules_triggered: list, stripe_pi_id: Optional[str],
        metadata: Optional[dict],
    ):
        await self.db.execute(
            """INSERT OR IGNORE INTO transactions
            (id, card_bin, card_fingerprint, amount, currency, customer_ip,
             customer_email, customer_id, risk_score, decision, signals,
             rules_triggered, stripe_payment_intent_id, metadata, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (id, card_bin, card_fingerprint, amount, currency, customer_ip,
             customer_email, customer_id, risk_score, decision,
             json.dumps(signals), json.dumps(rules_triggered), stripe_pi_id,
             json.dumps(metadata or {}), datetime.utcnow().isoformat())
        )
        await self.db.commit()

    async def get_transactions(
        self, decision: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> list[dict]:
        query = "SELECT * FROM transactions"
        params = []
        if decision:
            query += " WHERE decision = ?"
            params.append(decision)
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = await self.db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_transaction(self, txn_id: str) -> Optional[dict]:
        cursor = await self.db.execute("SELECT * FROM transactions WHERE id = ?", (txn_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    # --- Dashboard ---

    async def get_summary(self, hours: int = 24) -> dict:
        since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

        cursor = await self.db.execute(
            "SELECT decision, COUNT(*) as cnt FROM transactions WHERE created_at >= ? GROUP BY decision",
            (since,)
        )
        rows = await cursor.fetchall()
        counts = {r["decision"]: r["cnt"] for r in rows}

        total = sum(counts.values())
        disputes = await self.db.execute(
            "SELECT COUNT(*) as cnt FROM stripe_events WHERE event_type LIKE '%dispute%' AND processed_at >= ?",
            (since,)
        )
        dispute_row = await disputes.fetchone()

        return {
            "total_screened": total,
            "total_approved": counts.get("approve", 0),
            "total_blocked": counts.get("block", 0),
            "total_flagged": counts.get("flag", 0),
            "block_rate": counts.get("block", 0) / total if total > 0 else 0,
            "dispute_count": dispute_row["cnt"] if dispute_row else 0,
        }

    async def get_risk_trend(self, hours: int = 24, bucket_minutes: int = 60) -> list[dict]:
        since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        cursor = await self.db.execute(
            """SELECT
                substr(created_at, 1, 13) as hour,
                AVG(risk_score) as avg_score,
                COUNT(*) as count,
                SUM(CASE WHEN decision = 'block' THEN 1 ELSE 0 END) as blocks
            FROM transactions WHERE created_at >= ?
            GROUP BY hour ORDER BY hour""",
            (since,)
        )
        return [dict(r) for r in await cursor.fetchall()]

    async def get_top_bins(self, limit: int = 10) -> list[dict]:
        cursor = await self.db.execute(
            """SELECT bin, total_screens, total_blocks, total_disputes, risk_ratio
            FROM bin_risk_stats ORDER BY risk_ratio DESC LIMIT ?""",
            (limit,)
        )
        return [dict(r) for r in await cursor.fetchall()]

    # --- Rules ---

    async def get_rules(self, enabled_only: bool = False) -> list[dict]:
        query = "SELECT * FROM rules"
        if enabled_only:
            query += " WHERE enabled = 1"
        query += " ORDER BY priority DESC"
        cursor = await self.db.execute(query)
        return [dict(r) for r in await cursor.fetchall()]

    async def get_rule(self, rule_id: str) -> Optional[dict]:
        cursor = await self.db.execute("SELECT * FROM rules WHERE id = ?", (rule_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def create_rule(self, id: str, name: str, field: str, operator: str,
                          value: str, action: str, priority: int, enabled: bool):
        now = datetime.utcnow().isoformat()
        await self.db.execute(
            "INSERT INTO rules (id, name, field, operator, value, action, priority, enabled, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (id, name, field, operator, value, action, priority, int(enabled), now, now)
        )
        await self.db.commit()

    async def update_rule(self, rule_id: str, updates: dict):
        if not updates:
            return
        updates["updated_at"] = datetime.utcnow().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [rule_id]
        await self.db.execute(f"UPDATE rules SET {set_clause} WHERE id = ?", values)
        await self.db.commit()

    async def delete_rule(self, rule_id: str):
        await self.db.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
        await self.db.commit()

    # --- BIN ---

    async def get_bin_cache(self, bin: str) -> Optional[dict]:
        cursor = await self.db.execute("SELECT * FROM bin_cache WHERE bin = ?", (bin,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def save_bin_cache(self, bin: str, issuer: Optional[str], country: Optional[str],
                             card_type: str, is_prepaid: bool):
        await self.db.execute(
            "INSERT OR REPLACE INTO bin_cache (bin, issuer, country, card_type, is_prepaid, fetched_at) VALUES (?,?,?,?,?,?)",
            (bin, issuer, country, card_type, int(is_prepaid), datetime.utcnow().isoformat())
        )
        await self.db.commit()

    async def update_bin_risk(self, bin: str, blocked: bool = False, disputed: bool = False):
        now = datetime.utcnow().isoformat()
        await self.db.execute(
            """INSERT INTO bin_risk_stats (bin, total_screens, total_blocks, total_disputes, risk_ratio, updated_at)
            VALUES (?, 1, ?, ?, 0.0, ?)
            ON CONFLICT(bin) DO UPDATE SET
                total_screens = total_screens + 1,
                total_blocks = total_blocks + ?,
                total_disputes = total_disputes + ?,
                risk_ratio = CAST(total_blocks + total_disputes AS REAL) / MAX(total_screens, 1),
                updated_at = ?""",
            (bin, int(blocked), int(disputed), now, int(blocked), int(disputed), now)
        )
        await self.db.commit()

    async def get_bin_risk(self, bin: str) -> Optional[dict]:
        cursor = await self.db.execute("SELECT * FROM bin_risk_stats WHERE bin = ?", (bin,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    # --- Stripe Events ---

    async def save_stripe_event(self, id: str, event_type: str, payment_intent_id: Optional[str],
                                charge_id: Optional[str], dispute_id: Optional[str],
                                amount: Optional[int], reason: Optional[str], payload: str):
        await self.db.execute(
            """INSERT OR IGNORE INTO stripe_events
            (id, event_type, payment_intent_id, charge_id, dispute_id, amount, reason, payload, processed_at)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (id, event_type, payment_intent_id, charge_id, dispute_id, amount, reason, payload,
             datetime.utcnow().isoformat())
        )
        await self.db.commit()

    async def find_transaction_by_stripe_pi(self, pi_id: str) -> Optional[dict]:
        cursor = await self.db.execute(
            "SELECT * FROM transactions WHERE stripe_payment_intent_id = ?", (pi_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
