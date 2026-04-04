from __future__ import annotations

from app.db.engine import get_db
from app.db.repository import Repository
from app.services.bin_service import BINService
from app.services.risk_engine import RiskEngine
from app.services.rule_engine import RuleEngine
from app.services.stripe_service import StripeService
from app.services.velocity_service import VelocityService

# Shared instances (set during app lifespan)
_redis = None
_rule_engine: RuleEngine | None = None


def set_redis(redis):
    global _redis
    _redis = redis


def set_rule_engine(engine: RuleEngine):
    global _rule_engine
    _rule_engine = engine


async def get_risk_engine() -> RiskEngine:
    db = await get_db()
    repo = Repository(db)
    velocity = VelocityService(_redis)
    bin_service = BINService(repo)

    if _rule_engine:
        rule_engine = _rule_engine
    else:
        rule_engine = RuleEngine(repo)

    return RiskEngine(repo, velocity, bin_service, rule_engine)


async def get_repo() -> Repository:
    db = await get_db()
    return Repository(db)


async def get_stripe_service() -> StripeService:
    db = await get_db()
    repo = Repository(db)
    return StripeService(repo)


def get_rule_engine() -> RuleEngine:
    return _rule_engine
