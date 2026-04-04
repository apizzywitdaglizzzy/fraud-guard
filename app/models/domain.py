from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.enums import CardType, RiskDecision, RuleAction, RuleField


# --- Screen ---

class ScreenRequest(BaseModel):
    card_bin: str = Field(..., min_length=6, max_length=8)
    card_last4: str = Field(..., min_length=4, max_length=4)
    card_exp_month: int = Field(..., ge=1, le=12)
    card_exp_year: int = Field(..., ge=2024)
    amount: int = Field(..., gt=0, description="Amount in cents")
    currency: str = "usd"
    customer_ip: str
    customer_email: Optional[str] = None
    customer_id: Optional[str] = None
    metadata: Optional[dict] = None


class RiskSignal(BaseModel):
    name: str
    weight: float
    detail: str


class BINInfo(BaseModel):
    bin: str
    issuer: Optional[str] = None
    country: Optional[str] = None
    card_type: CardType = CardType.UNKNOWN
    is_prepaid: bool = False
    risk_level: str = "unknown"


class VelocitySummary(BaseModel):
    ip_attempts_1m: int = 0
    ip_attempts_1h: int = 0
    ip_attempts_24h: int = 0
    card_attempts_1h: int = 0
    card_attempts_24h: int = 0
    email_attempts_1h: int = 0
    email_attempts_24h: int = 0


class ScreenResponse(BaseModel):
    decision: RiskDecision
    risk_score: float
    signals: list[RiskSignal]
    transaction_id: str
    bin_info: Optional[BINInfo] = None
    velocity: VelocitySummary
    rules_triggered: list[str]
    screened_at: datetime


# --- Charge (screen + forward) ---

class ChargeRequest(BaseModel):
    card_bin: str = Field(..., min_length=6, max_length=8)
    card_last4: str = Field(..., min_length=4, max_length=4)
    card_exp_month: int = Field(..., ge=1, le=12)
    card_exp_year: int = Field(..., ge=2024)
    amount: int = Field(..., gt=0)
    currency: str = "usd"
    customer_ip: str
    customer_email: Optional[str] = None
    customer_id: Optional[str] = None
    payment_method_id: str = Field(..., description="Stripe payment method ID")
    metadata: Optional[dict] = None


class ChargeResponse(BaseModel):
    screening: ScreenResponse
    stripe_payment_intent_id: Optional[str] = None
    stripe_status: Optional[str] = None
    charged: bool = False


# --- Rules ---

class RuleCreate(BaseModel):
    name: str
    field: RuleField
    operator: str = Field(..., pattern="^(eq|neq|in|not_in|gt|lt|gte|lte)$")
    value: Any
    action: RuleAction
    priority: int = 0
    enabled: bool = True


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    field: Optional[RuleField] = None
    operator: Optional[str] = None
    value: Optional[Any] = None
    action: Optional[RuleAction] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None


class RuleResponse(BaseModel):
    id: str
    name: str
    field: RuleField
    operator: str
    value: Any
    action: RuleAction
    priority: int
    enabled: bool
    created_at: datetime
    updated_at: datetime


# --- Dashboard ---

class DashboardSummary(BaseModel):
    total_screened: int
    total_approved: int
    total_blocked: int
    total_flagged: int
    block_rate: float
    dispute_count: int
    period: str


class TransactionRecord(BaseModel):
    id: str
    card_bin: str
    card_fingerprint: str
    amount: int
    currency: str
    customer_ip: str
    risk_score: float
    decision: RiskDecision
    rules_triggered: list[str]
    created_at: datetime


# --- Errors ---

class FraudGuardError(Exception):
    def __init__(self, message: str, code: str = "internal_error"):
        self.message = message
        self.code = code
        super().__init__(message)


class BINLookupError(FraudGuardError):
    def __init__(self, message: str = "BIN lookup failed"):
        super().__init__(message, "bin_lookup_failed")


class VelocityServiceError(FraudGuardError):
    def __init__(self, message: str = "Velocity service unavailable"):
        super().__init__(message, "velocity_service_error")


class StripeForwardError(FraudGuardError):
    def __init__(self, message: str = "Stripe forwarding failed"):
        super().__init__(message, "stripe_forward_error")
