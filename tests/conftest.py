from __future__ import annotations

import asyncio
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
DB_PATH = _tmp.name

os.environ["FRAUDGUARD_API_KEY"] = "test_key"
os.environ["FRAUDGUARD_USE_FAKE_REDIS"] = "true"
os.environ["FRAUDGUARD_DEBUG"] = "true"
os.environ["FRAUDGUARD_DATABASE_URL"] = f"sqlite+aiosqlite:///{DB_PATH}"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_app(event_loop):
    """Initialize DB, redis, and rule engine before tests."""
    import fakeredis.aioredis
    from app.db.engine import set_db_path
    from app.db.migrations import init_db
    from app.dependencies import set_redis, set_rule_engine
    from app.db.engine import get_db
    from app.db.repository import Repository
    from app.services.rule_engine import RuleEngine

    set_db_path(DB_PATH)
    event_loop.run_until_complete(init_db(DB_PATH))

    redis = fakeredis.aioredis.FakeRedis()
    set_redis(redis)

    async def _setup_rules():
        db = await get_db()
        repo = Repository(db)
        engine = RuleEngine(repo)
        await engine.load_rules()
        set_rule_engine(engine)

    event_loop.run_until_complete(_setup_rules())
    yield


@pytest.fixture(scope="session")
def test_app(setup_app):
    from app.main import app
    return app


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test_key", "Content-Type": "application/json"}


@pytest.fixture
def sample_screen_request():
    return {
        "card_bin": "411111",
        "card_last4": "1234",
        "card_exp_month": 12,
        "card_exp_year": 2026,
        "amount": 5000,
        "currency": "usd",
        "customer_ip": "73.162.45.89",
        "customer_email": "test@example.com",
    }
