import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Read from the environment on every call so tests can override values."""

    env: str
    database_url: str
    response_window_days: int
    checkpoint_key: str


def get_settings() -> Settings:
    return Settings(
        env=os.getenv("APN_ENV", ""),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./case_core.db"),
        response_window_days=int(os.getenv("APN_RESPONSE_WINDOW_DAYS", "10")),
        checkpoint_key=os.getenv("APN_CHECKPOINT_KEY", ""),
    )
