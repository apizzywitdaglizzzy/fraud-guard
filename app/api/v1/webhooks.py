from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.dependencies import get_stripe_service
from app.services.stripe_service import StripeService
from app.models.domain import StripeForwardError

router = APIRouter()


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_svc: StripeService = Depends(get_stripe_service),
):
    """Receive Stripe webhook events (disputes, failures, refunds)."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe_svc.verify_webhook(payload, sig_header)
    except StripeForwardError as e:
        raise HTTPException(status_code=400, detail=e.message)

    await stripe_svc.process_webhook_event(event)
    return {"status": "processed", "event_id": event["id"]}
