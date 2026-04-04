from __future__ import annotations

from app.config import settings
from app.models.domain import BINInfo, RiskSignal, ScreenRequest, VelocitySummary
from app.models.enums import CardType


def calculate(
    request: ScreenRequest, bin_info: BINInfo, velocity: VelocitySummary
) -> tuple[float, list[RiskSignal]]:
    """Calculate risk score from signals. Returns (score, signals)."""
    signals = []
    score = 0.0

    # 1. BIN country risk (weight: 0.20)
    if bin_info.country and bin_info.country in settings.high_risk_countries:
        weight = 0.20
        score += weight
        signals.append(RiskSignal(
            name="high_risk_country",
            weight=weight,
            detail=f"Card issued in high-risk country: {bin_info.country}",
        ))

    # 2. Prepaid card (weight: 0.15)
    if bin_info.is_prepaid:
        weight = 0.15
        score += weight
        signals.append(RiskSignal(
            name="prepaid_card",
            weight=weight,
            detail="Card is prepaid — higher fraud risk",
        ))

    # 3. BIN historical risk (weight: 0.20)
    if bin_info.risk_level == "high":
        weight = 0.20
        score += weight
        signals.append(RiskSignal(
            name="high_risk_bin",
            weight=weight,
            detail=f"BIN {bin_info.bin} has high historical dispute/block ratio",
        ))
    elif bin_info.risk_level == "medium":
        weight = 0.10
        score += weight
        signals.append(RiskSignal(
            name="medium_risk_bin",
            weight=weight,
            detail=f"BIN {bin_info.bin} has elevated historical risk",
        ))

    # 4. IP velocity (weight: 0.15)
    if velocity.ip_attempts_1m > settings.velocity_ip_1m:
        weight = 0.15
        score += weight
        signals.append(RiskSignal(
            name="high_velocity_ip_1m",
            weight=weight,
            detail=f"IP has {velocity.ip_attempts_1m} attempts in last minute (threshold: {settings.velocity_ip_1m})",
        ))
    elif velocity.ip_attempts_1h > settings.velocity_ip_1h:
        weight = 0.10
        score += weight
        signals.append(RiskSignal(
            name="high_velocity_ip_1h",
            weight=weight,
            detail=f"IP has {velocity.ip_attempts_1h} attempts in last hour (threshold: {settings.velocity_ip_1h})",
        ))

    # 5. Card velocity (weight: 0.15)
    if velocity.card_attempts_1h > settings.velocity_card_1h:
        weight = 0.15
        score += weight
        signals.append(RiskSignal(
            name="high_velocity_card",
            weight=weight,
            detail=f"Card used {velocity.card_attempts_1h} times in last hour (threshold: {settings.velocity_card_1h})",
        ))

    # 6. Email velocity (weight: 0.10)
    if velocity.email_attempts_1h > settings.velocity_email_1h:
        weight = 0.10
        score += weight
        signals.append(RiskSignal(
            name="high_velocity_email",
            weight=weight,
            detail=f"Email has {velocity.email_attempts_1h} attempts in last hour (threshold: {settings.velocity_email_1h})",
        ))

    # 7. High amount (weight: 0.05)
    if request.amount > settings.high_amount_threshold:
        weight = 0.05
        score += weight
        signals.append(RiskSignal(
            name="high_amount",
            weight=weight,
            detail=f"Amount ${request.amount / 100:.2f} exceeds threshold ${settings.high_amount_threshold / 100:.2f}",
        ))

    return min(score, 1.0), signals
