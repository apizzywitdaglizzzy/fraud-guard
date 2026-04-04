"""Seed default fraud prevention rules."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aiosqlite

DEFAULT_RULES = [
    {
        "name": "Block prepaid cards",
        "field": "is_prepaid",
        "operator": "eq",
        "value": True,
        "action": "block",
        "priority": 10,
    },
    {
        "name": "Flag high-risk countries",
        "field": "country",
        "operator": "in",
        "value": ["NG", "GH", "PK", "BD", "VN"],
        "action": "flag",
        "priority": 8,
    },
    {
        "name": "Block card testing (IP >10/min)",
        "field": "velocity_ip_1m",
        "operator": "gt",
        "value": 10,
        "action": "block",
        "priority": 100,
    },
    {
        "name": "Flag rapid IP activity (>30/hr)",
        "field": "velocity_ip_1h",
        "operator": "gt",
        "value": 30,
        "action": "flag",
        "priority": 50,
    },
    {
        "name": "Block card reuse (>5/hr)",
        "field": "velocity_card_1h",
        "operator": "gt",
        "value": 5,
        "action": "block",
        "priority": 90,
    },
    {
        "name": "Flag high amount (>$500)",
        "field": "amount",
        "operator": "gt",
        "value": 50000,
        "action": "flag",
        "priority": 5,
    },
]


async def seed():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "fraudguard.db")
    async with aiosqlite.connect(db_path) as db:
        now = datetime.utcnow().isoformat()
        for rule in DEFAULT_RULES:
            rule_id = f"rule_{uuid.uuid4().hex[:12]}"
            try:
                await db.execute(
                    "INSERT INTO rules (id, name, field, operator, value, action, priority, enabled, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (rule_id, rule["name"], rule["field"], rule["operator"],
                     json.dumps(rule["value"]), rule["action"], rule["priority"], 1, now, now)
                )
                print(f"  + {rule['name']}")
            except Exception as e:
                print(f"  ! {rule['name']} (already exists or error: {e})")
        await db.commit()
    print("\nDone. Default rules seeded.")


if __name__ == "__main__":
    asyncio.run(seed())
