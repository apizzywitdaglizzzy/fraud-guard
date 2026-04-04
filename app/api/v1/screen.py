from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_risk_engine
from app.models.domain import ScreenRequest, ScreenResponse
from app.services.risk_engine import RiskEngine

router = APIRouter()


@router.post("/screen", response_model=ScreenResponse)
async def screen_transaction(
    request: ScreenRequest,
    engine: RiskEngine = Depends(get_risk_engine),
):
    """Screen a transaction for fraud risk before charging."""
    return await engine.screen(request)
