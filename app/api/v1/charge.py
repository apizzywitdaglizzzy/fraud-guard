from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_risk_engine, get_stripe_service
from app.models.domain import ChargeRequest, ChargeResponse, ScreenRequest
from app.models.enums import RiskDecision
from app.services.risk_engine import RiskEngine
from app.services.stripe_service import StripeService

router = APIRouter()


@router.post("/charge", response_model=ChargeResponse)
async def screen_and_charge(
    request: ChargeRequest,
    engine: RiskEngine = Depends(get_risk_engine),
    stripe_svc: StripeService = Depends(get_stripe_service),
):
    """Screen a transaction, then charge via Stripe if approved."""
    screen_req = ScreenRequest(
        card_bin=request.card_bin,
        card_last4=request.card_last4,
        card_exp_month=request.card_exp_month,
        card_exp_year=request.card_exp_year,
        amount=request.amount,
        currency=request.currency,
        customer_ip=request.customer_ip,
        customer_email=request.customer_email,
        customer_id=request.customer_id,
        metadata=request.metadata,
    )

    screening = await engine.screen(screen_req)

    if screening.decision == RiskDecision.BLOCK:
        return ChargeResponse(screening=screening, charged=False)

    # Forward to Stripe
    try:
        result = await stripe_svc.create_payment_intent(
            amount=request.amount,
            currency=request.currency,
            payment_method_id=request.payment_method_id,
            metadata={"fraudguard_txn": screening.transaction_id},
        )
        return ChargeResponse(
            screening=screening,
            stripe_payment_intent_id=result["id"],
            stripe_status=result["status"],
            charged=True,
        )
    except Exception as e:
        return ChargeResponse(
            screening=screening,
            stripe_status=str(e),
            charged=False,
        )
