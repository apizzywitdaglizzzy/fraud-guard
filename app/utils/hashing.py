from __future__ import annotations

import hashlib


def card_fingerprint(bin: str, last4: str, exp_month: int, exp_year: int) -> str:
    raw = f"{bin}:{last4}:{exp_month}:{exp_year}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
