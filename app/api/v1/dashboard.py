from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.db.repository import Repository
from app.dependencies import get_repo
from app.models.domain import DashboardSummary, TransactionRecord

router = APIRouter(prefix="/dashboard")


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(
    hours: int = Query(24, ge=1, le=720),
    repo: Repository = Depends(get_repo),
):
    """Get screening summary stats."""
    stats = await repo.get_summary(hours=hours)
    return DashboardSummary(
        total_screened=stats["total_screened"],
        total_approved=stats["total_approved"],
        total_blocked=stats["total_blocked"],
        total_flagged=stats["total_flagged"],
        block_rate=stats["block_rate"],
        dispute_count=stats["dispute_count"],
        period=f"last_{hours}h",
    )


@router.get("/transactions", response_model=list[TransactionRecord])
async def get_transactions(
    decision: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    repo: Repository = Depends(get_repo),
):
    """List transactions with optional filtering."""
    rows = await repo.get_transactions(decision=decision, limit=limit, offset=offset)
    return [_row_to_record(r) for r in rows]


@router.get("/blocked", response_model=list[TransactionRecord])
async def get_blocked(
    limit: int = Query(50, ge=1, le=500),
    repo: Repository = Depends(get_repo),
):
    """List blocked transactions."""
    rows = await repo.get_transactions(decision="block", limit=limit)
    return [_row_to_record(r) for r in rows]


@router.get("/risk-trend")
async def get_risk_trend(
    hours: int = Query(24, ge=1, le=720),
    repo: Repository = Depends(get_repo),
):
    """Get hourly risk score averages."""
    return await repo.get_risk_trend(hours=hours)


@router.get("/top-bins")
async def get_top_bins(
    limit: int = Query(10, ge=1, le=100),
    repo: Repository = Depends(get_repo),
):
    """Get BINs ranked by risk ratio."""
    return await repo.get_top_bins(limit=limit)


def _row_to_record(row: dict) -> TransactionRecord:
    return TransactionRecord(
        id=row["id"], card_bin=row["card_bin"],
        card_fingerprint=row["card_fingerprint"],
        amount=row["amount"], currency=row["currency"],
        customer_ip=row["customer_ip"],
        risk_score=row["risk_score"], decision=row["decision"],
        rules_triggered=json.loads(row["rules_triggered"]),
        created_at=row["created_at"],
    )
