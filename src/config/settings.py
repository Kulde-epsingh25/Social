"""Configuration settings loaded from environment variables."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration sourced from environment variables or .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── News / Media ──────────────────────────────────────────────────────────
    news_api_key: str = Field(default="", alias="NEWS_API_KEY")
    news_api_url: str = Field(
        default="https://newsdata.io/api/1", alias="NEWS_API_URL"
    )

    # ── OpenAI ────────────────────────────────────────────────────────────────
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", alias="OPENAI_MODEL")

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost", alias="REDIS_URL")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")

    # ── X (Twitter) ───────────────────────────────────────────────────────────
    x_api_key: str = Field(default="", alias="X_API_KEY")
    x_api_secret: str = Field(default="", alias="X_API_SECRET")
    x_access_token: str = Field(default="", alias="X_ACCESS_TOKEN")
    x_access_token_secret: str = Field(default="", alias="X_ACCESS_TOKEN_SECRET")

    # ── Kafka ─────────────────────────────────────────────────────────────────
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092", alias="KAFKA_BOOTSTRAP_SERVERS"
    )

    # ── OGD / FIR ─────────────────────────────────────────────────────────────
    ogd_api_key: str = Field(default="", alias="OGD_API_KEY")

    # ── Legislative ───────────────────────────────────────────────────────────
    prs_base_url: str = Field(
        default="https://prsindia.org/api", alias="PRS_BASE_URL"
    )
    digital_sansad_url: str = Field(
        default="https://digitalsansad.sansad.in", alias="DIGITAL_SANSAD_URL"
    )
    adr_base_url: str = Field(default="https://myneta.info", alias="ADR_BASE_URL")

    # ── Fact-checking ─────────────────────────────────────────────────────────
    originality_api_key: str = Field(default="", alias="ORIGINALITY_API_KEY")

    # ── Posting limits ────────────────────────────────────────────────────────
    max_posts_per_day: int = Field(default=10, alias="MAX_POSTS_PER_DAY")
    post_interval_minutes: int = Field(default=60, alias="POST_INTERVAL_MINUTES")

    # ── HITL ──────────────────────────────────────────────────────────────────
    hitl_enabled: bool = Field(default=True, alias="HITL_ENABLED")

    # ── AI Labeling ───────────────────────────────────────────────────────────
    ai_label_prefix: str = Field(
        default="[AI-Generated]", alias="AI_LABEL_PREFIX"
    )


# Module-level singleton – import this throughout the codebase.
settings = Settings()
