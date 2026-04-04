from __future__ import annotations

from fastapi import APIRouter, Depends

from app.db.repository import Repository
from app.dependencies import get_repo
from app.models.domain import BINInfo
from app.services.bin_service import BINService

router = APIRouter()


@router.get("/bin/{bin}", response_model=BINInfo)
async def lookup_bin(bin: str, repo: Repository = Depends(get_repo)):
    """Look up card BIN information and risk level."""
    service = BINService(repo)
    return await service.lookup(bin)
