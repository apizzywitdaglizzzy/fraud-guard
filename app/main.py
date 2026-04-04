from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.db.engine import get_db, set_db_path
from app.db.migrations import init_db
from app.db.repository import Repository
from app.dependencies import set_redis, set_rule_engine
from app.models.domain import FraudGuardError
from app.services.rule_engine import RuleEngine

logger = logging.getLogger("fraudguard")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    # Database
    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    set_db_path(db_path)
    await init_db(db_path)
    logger.info(f"Database initialized: {db_path}")

    # Redis
    if settings.use_fake_redis:
        import fakeredis.aioredis
        redis = fakeredis.aioredis.FakeRedis()
        logger.info("Using fake Redis (dev mode)")
    else:
        import redis.asyncio as aioredis
        redis = aioredis.from_url(settings.redis_url)
        logger.info(f"Connected to Redis: {settings.redis_url}")
    set_redis(redis)

    # Rule engine
    db = await get_db()
    repo = Repository(db)
    rule_engine = RuleEngine(repo)
    await rule_engine.load_rules()
    set_rule_engine(rule_engine)
    logger.info("Rule engine loaded")

    logger.info(f"FraudGuard started (debug={settings.debug})")

    yield

    # Shutdown
    await redis.aclose()
    await db.close()
    logger.info("FraudGuard shut down")


app = FastAPI(
    title="FraudGuard",
    description="Developer-first fraud prevention middleware for Stripe",
    version="0.1.0",
    lifespan=lifespan,
)


# Error handler
@app.exception_handler(FraudGuardError)
async def fraudguard_error_handler(request: Request, exc: FraudGuardError):
    return JSONResponse(
        status_code=500,
        content={"error": exc.code, "detail": exc.message},
    )


# Health check
@app.get("/health")
async def health():
    return {"status": "ok", "service": "fraudguard", "version": "0.1.0"}


# Mount API
from app.api.v1.router import router as v1_router  # noqa: E402
app.include_router(v1_router)
