from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

import httpx

from app.config import settings
from app.db.repository import Repository
from app.models.domain import BINInfo, BINLookupError
from app.models.enums import CardType

logger = logging.getLogger(__name__)

BINLIST_URL = "https://lookup.binlist.net"


class BINService:
    def __init__(self, repo: Repository):
        self.repo = repo

    async def lookup(self, bin: str) -> BINInfo:
        # Check cache first
        cached = await self.repo.get_bin_cache(bin)
        if cached:
            fetched = datetime.fromisoformat(cached["fetched_at"])
            if datetime.utcnow() - fetched < timedelta(days=settings.bin_cache_ttl_days):
                risk = await self._get_risk_level(bin)
                return BINInfo(
                    bin=bin,
                    issuer=cached["issuer"],
                    country=cached["country"],
                    card_type=CardType(cached["card_type"]) if cached["card_type"] else CardType.UNKNOWN,
                    is_prepaid=bool(cached["is_prepaid"]),
                    risk_level=risk,
                )

        # Fetch from binlist.net
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{BINLIST_URL}/{bin}",
                    headers={"Accept-Version": "3"},
                    timeout=5.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    card_type = self._parse_card_type(data)
                    is_prepaid = data.get("prepaid", False) or False
                    country = data.get("country", {}).get("alpha2")
                    issuer = data.get("bank", {}).get("name")

                    await self.repo.save_bin_cache(bin, issuer, country, card_type.value, is_prepaid)

                    risk = await self._get_risk_level(bin)
                    return BINInfo(
                        bin=bin, issuer=issuer, country=country,
                        card_type=card_type, is_prepaid=is_prepaid, risk_level=risk,
                    )
                elif resp.status_code == 404:
                    # BIN not in database — return unknown
                    await self.repo.save_bin_cache(bin, None, None, CardType.UNKNOWN.value, False)
                    return BINInfo(bin=bin, risk_level=await self._get_risk_level(bin))
                elif resp.status_code == 429:
                    logger.warning("BIN lookup rate limited")
                    return BINInfo(bin=bin, risk_level="unknown")
                else:
                    logger.warning(f"BIN lookup returned {resp.status_code}")
                    return BINInfo(bin=bin, risk_level="unknown")

        except httpx.RequestError as e:
            logger.warning(f"BIN lookup network error: {e}")
            return BINInfo(bin=bin, risk_level="unknown")

    async def update_risk_stats(self, bin: str, blocked: bool = False, disputed: bool = False):
        await self.repo.update_bin_risk(bin, blocked=blocked, disputed=disputed)

    async def _get_risk_level(self, bin: str) -> str:
        stats = await self.repo.get_bin_risk(bin)
        if not stats or stats["total_screens"] < 5:
            return "unknown"
        ratio = stats["risk_ratio"]
        if ratio > 0.3:
            return "high"
        elif ratio > 0.1:
            return "medium"
        return "low"

    def _parse_card_type(self, data: dict) -> CardType:
        if data.get("prepaid"):
            return CardType.PREPAID
        scheme_type = data.get("type", "").lower()
        if "debit" in scheme_type:
            return CardType.DEBIT
        if "credit" in scheme_type:
            return CardType.CREDIT
        return CardType.UNKNOWN
