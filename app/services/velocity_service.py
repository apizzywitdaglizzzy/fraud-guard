from __future__ import annotations

import time
from typing import Optional

from app.models.domain import VelocitySummary


class VelocityService:
    """Redis-backed sliding window velocity counters."""

    def __init__(self, redis):
        self.redis = redis

    async def check_and_increment(
        self, card_fingerprint: str, ip: str, email: Optional[str] = None
    ) -> VelocitySummary:
        now = time.time()

        ip_1m, ip_1h, ip_24h = await self._count_and_add(f"velocity:ip:{ip}", now, [60, 3600, 86400])
        card_1h, card_24h = await self._count_and_add(f"velocity:card:{card_fingerprint}", now, [3600, 86400])

        email_1h, email_24h = 0, 0
        if email:
            email_1h, email_24h = await self._count_and_add(f"velocity:email:{email}", now, [3600, 86400])

        return VelocitySummary(
            ip_attempts_1m=ip_1m,
            ip_attempts_1h=ip_1h,
            ip_attempts_24h=ip_24h,
            card_attempts_1h=card_1h,
            card_attempts_24h=card_24h,
            email_attempts_1h=email_1h,
            email_attempts_24h=email_24h,
        )

    async def _count_and_add(self, key: str, now: float, windows: list[int]) -> tuple:
        """Add current timestamp and count entries in each window."""
        # Add the current event
        await self.redis.zadd(key, {str(now): now})

        # Prune entries older than the largest window
        max_window = max(windows)
        await self.redis.zremrangebyscore(key, 0, now - max_window)

        # Set TTL so keys don't live forever
        await self.redis.expire(key, max_window + 60)

        # Count entries in each window
        counts = []
        for window in windows:
            count = await self.redis.zcount(key, now - window, now)
            counts.append(count)

        return tuple(counts)
