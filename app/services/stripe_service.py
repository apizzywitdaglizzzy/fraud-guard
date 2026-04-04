from __future__ import annotations

import json
import logging
from typing import Optional

import stripe

from app.config import settings
from app.db.repository import Repository
from app.models.domain import StripeForwardError

logger = logging.getLogger(__name__)


class StripeService:
    def __init__(self, repo: Repository):
        self.repo = repo
        if settings.stripe_api_key:
            stripe.api_key = settings.stripe_api_key

    async def create_payment_intent(
        self, amount: int, currency: str, payment_method_id: str,
        metadata: Optional[dict] = None,
    ) -> dict:
        if not settings.stripe_api_key:
            raise StripeForwardError("Stripe API key not configured")

        try:
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                payment_method=payment_method_id,
                confirm=True,
                automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
                metadata=metadata or {},
            )
            return {
                "id": intent.id,
                "status": intent.status,
                "amount": intent.amount,
                "currency": intent.currency,
            }
        except stripe.StripeError as e:
            raise StripeForwardError(f"Stripe error: {e.user_message or str(e)}")

    def verify_webhook(self, payload: bytes, sig_header: str) -> dict:
        if not settings.stripe_webhook_secret:
            raise StripeForwardError("Stripe webhook secret not configured")

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret,
            )
            return event
        except (stripe.SignatureVerificationError, ValueError) as e:
            raise StripeForwardError(f"Webhook verification failed: {e}")

    async def process_webhook_event(self, event: dict):
        event_type = event["type"]
        event_id = event["id"]
        obj = event["data"]["object"]

        payment_intent_id = None
        charge_id = None
        dispute_id = None
        amount = None
        reason = None

        if event_type.startswith("charge.dispute"):
            dispute_id = obj.get("id")
            charge_id = obj.get("charge")
            payment_intent_id = obj.get("payment_intent")
            amount = obj.get("amount")
            reason = obj.get("reason")

            # Update BIN risk if we can find the original transaction
            if payment_intent_id:
                txn = await self.repo.find_transaction_by_stripe_pi(payment_intent_id)
                if txn:
                    await self.repo.update_bin_risk(txn["card_bin"], disputed=True)

        elif event_type == "charge.failed":
            charge_id = obj.get("id")
            payment_intent_id = obj.get("payment_intent")
            amount = obj.get("amount")
            reason = obj.get("failure_message")

        elif event_type == "charge.refunded":
            charge_id = obj.get("id")
            payment_intent_id = obj.get("payment_intent")
            amount = obj.get("amount_refunded")

        await self.repo.save_stripe_event(
            id=event_id, event_type=event_type,
            payment_intent_id=payment_intent_id, charge_id=charge_id,
            dispute_id=dispute_id, amount=amount, reason=reason,
            payload=json.dumps(event),
        )

        logger.info(f"Processed Stripe event: {event_type} ({event_id})")
