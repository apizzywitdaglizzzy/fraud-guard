from __future__ import annotations

from fastapi import Header, HTTPException

from app.config import settings


async def verify_api_key(authorization: str = Header(...)):
    expected = f"Bearer {settings.api_key}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")
