from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.middleware import verify_api_key
from app.api.v1 import screen, charge, rules, bin_lookup, dashboard, dashboard_html, webhooks

router = APIRouter(prefix="/v1")

# Authenticated routes
authed = APIRouter(dependencies=[Depends(verify_api_key)])
authed.include_router(screen.router)
authed.include_router(charge.router)
authed.include_router(rules.router)
authed.include_router(bin_lookup.router)
authed.include_router(dashboard.router)

router.include_router(authed)

# Webhook uses Stripe signature verification instead of API key
router.include_router(webhooks.router)

# HTML dashboard (no auth for dev)
router.include_router(dashboard_html.router)
