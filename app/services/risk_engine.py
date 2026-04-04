from __future__ import annotations

import asyncio
import uuid
from datetime import datetime

from app.config import settings
from app.db.repository import Repository
from app.models.domain import BINInfo, ScreenRequest, ScreenResponse, VelocitySummary
from app.models.enums import RiskDecision, RuleAction
from app.services.bin_service import BINService
from app.services.rule_engine import RuleEngine
from app.services.scoring import calculate
from app.services.velocity_service import VelocityService
from app.utils.hashing import card_fingerprint


class RiskEngine:
    def __init__(self, repo: Repository, velocity: VelocityService,
                 bin_service: BINService, rule_engine: RuleEngine):
        self.repo = repo
        self.velocity = velocity
        self.bin_service = bin_service
        self.rule_engine = rule_engine

    async def screen(self, request: ScreenRequest) -> ScreenResponse:
        txn_id = f"txn_{uuid.uuid4().hex[:16]}"
        fingerprint = card_fingerprint(
            request.card_bin, request.card_last4,
            request.card_exp_month, request.card_exp_year,
        )

        # Run BIN lookup and velocity check concurrently
        bin_info, velocity = await asyncio.gather(
            self._safe_bin_lookup(request.card_bin),
            self._safe_velocity_check(fingerprint, request.customer_ip, request.customer_email),
        )

        # Calculate risk score from signals
        risk_score, signals = calculate(request, bin_info, velocity)

        # Evaluate merchant rules (pass repo so rules can reload from current DB)
        triggered_rules, rule_action = await self.rule_engine.evaluate(request, bin_info, velocity, repo=self.repo)

        # Make decision
        decision = self._decide(risk_score, rule_action)

        # Update BIN risk stats
        await self.bin_service.update_risk_stats(
            request.card_bin, blocked=(decision == RiskDecision.BLOCK)
        )

        # Persist
        await self.repo.save_transaction(
            id=txn_id, card_bin=request.card_bin, card_fingerprint=fingerprint,
            amount=request.amount, currency=request.currency,
            customer_ip=request.customer_ip, customer_email=request.customer_email,
            customer_id=request.customer_id, risk_score=risk_score,
            decision=decision.value,
            signals=[s.model_dump() for s in signals],
            rules_triggered=triggered_rules,
            stripe_pi_id=None, metadata=request.metadata,
        )

        return ScreenResponse(
            decision=decision, risk_score=round(risk_score, 4),
            signals=signals, transaction_id=txn_id,
            bin_info=bin_info, velocity=velocity,
            rules_triggered=triggered_rules,
            screened_at=datetime.utcnow(),
        )

    def _decide(self, score: float, rule_action: RuleAction | None) -> RiskDecision:
        # Rules take precedence
        if rule_action == RuleAction.BLOCK:
            return RiskDecision.BLOCK
        if rule_action == RuleAction.ALLOW:
            return RiskDecision.APPROVE

        # Score-based decision
        if score >= settings.block_threshold:
            return RiskDecision.BLOCK
        if score >= settings.flag_threshold:
            return RiskDecision.FLAG
        if rule_action == RuleAction.FLAG:
            return RiskDecision.FLAG
        return RiskDecision.APPROVE

    async def _safe_bin_lookup(self, bin: str) -> BINInfo:
        try:
            return await self.bin_service.lookup(bin)
        except Exception:
            return BINInfo(bin=bin, risk_level="unknown")

    async def _safe_velocity_check(self, fingerprint: str, ip: str, email: str | None) -> VelocitySummary:
        try:
            return await self.velocity.check_and_increment(fingerprint, ip, email)
        except Exception:
            return VelocitySummary()
