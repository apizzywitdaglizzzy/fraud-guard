from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="FRAUDGUARD_")

    # App
    app_name: str = "FraudGuard"
    debug: bool = False
    api_key: str = "fg_test_key_dev_12345"
    port: int = 8000

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/fraudguard.db"

    # Redis — set use_fake_redis=false and provide redis_url for production
    # Railway auto-provides REDIS_URL when you add a Redis plugin
    redis_url: str = "redis://localhost:6379/0"
    use_fake_redis: bool = True

    # Stripe
    stripe_api_key: str = ""
    stripe_webhook_secret: str = ""

    # Risk thresholds
    flag_threshold: float = 0.5
    block_threshold: float = 0.8

    # Velocity limits
    velocity_ip_1m: int = 10
    velocity_ip_1h: int = 50
    velocity_card_1h: int = 5
    velocity_card_24h: int = 15
    velocity_email_1h: int = 20

    # BIN
    bin_cache_ttl_days: int = 30
    high_risk_countries: list[str] = ["NG", "GH", "PK", "BD", "VN"]

    # Amount
    high_amount_threshold: int = 50000  # cents ($500)


settings = Settings()
