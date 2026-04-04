from __future__ import annotations

import json
import logging
from typing import Any

from app.db.repository import Repository
from app.models.domain import BINInfo, ScreenRequest, VelocitySummary
from app.models.enums import RuleAction, RuleField

logger = logging.getLogger(__name__)


class RuleEngine:
    def __init__(self, repo: Repository):
        self.repo = repo
        self._rules_cache: list[dict] = []

    async def load_rules(self):
        self._rules_cache = await self.repo.get_rules(enabled_only=True)

    async def evaluate(
        self, request: ScreenRequest, bin_info: BINInfo, velocity: VelocitySummary,
        repo: Repository = None,
    ) -> tuple[list[str], RuleAction | None]:
        """Evaluate all rules. Returns (triggered_rule_names, most_severe_action)."""
        if not self._rules_cache:
            if repo:
                self.repo = repo
            await self.load_rules()

        triggered = []
        worst_action = None

        # Build the context that rules evaluate against
        context = self._build_context(request, bin_info, velocity)

        for rule in self._rules_cache:
            field = rule["field"]
            operator = rule["operator"]
            value = json.loads(rule["value"])
            action = RuleAction(rule["action"])

            actual = context.get(field)
            if actual is None:
                continue

            if self._matches(actual, operator, value):
                triggered.append(rule["name"])
                if worst_action is None or self._severity(action) > self._severity(worst_action):
                    worst_action = action

        return triggered, worst_action

    def invalidate_cache(self):
        self._rules_cache = []

    def _build_context(self, req: ScreenRequest, bin_info: BINInfo, velocity: VelocitySummary) -> dict:
        return {
            RuleField.COUNTRY.value: bin_info.country,
            RuleField.BIN.value: req.card_bin,
            RuleField.CARD_TYPE.value: bin_info.card_type.value if bin_info else "unknown",
            RuleField.IS_PREPAID.value: bin_info.is_prepaid if bin_info else False,
            RuleField.AMOUNT.value: req.amount,
            RuleField.VELOCITY_IP_1M.value: velocity.ip_attempts_1m,
            RuleField.VELOCITY_IP_1H.value: velocity.ip_attempts_1h,
            RuleField.VELOCITY_CARD_1H.value: velocity.card_attempts_1h,
            RuleField.VELOCITY_EMAIL_1H.value: velocity.email_attempts_1h,
        }

    def _matches(self, actual: Any, operator: str, value: Any) -> bool:
        try:
            if operator == "eq":
                return actual == value
            elif operator == "neq":
                return actual != value
            elif operator == "in":
                return actual in value
            elif operator == "not_in":
                return actual not in value
            elif operator == "gt":
                return float(actual) > float(value)
            elif operator == "lt":
                return float(actual) < float(value)
            elif operator == "gte":
                return float(actual) >= float(value)
            elif operator == "lte":
                return float(actual) <= float(value)
        except (TypeError, ValueError):
            return False
        return False

    def _severity(self, action: RuleAction) -> int:
        return {RuleAction.ALLOW: 0, RuleAction.FLAG: 1, RuleAction.BLOCK: 2}.get(action, 0)
