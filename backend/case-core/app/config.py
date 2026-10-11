import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Read from the environment on every call so tests can override values."""

    env: str
    database_url: str
    response_window_days: int
    decision_sla_hours: int
    checkpoint_key: str
    cors_origins: tuple[str, ...] = ()
    # Policy floors, in rupees. They are settings, not law: the amount of a challan or fine must come from the statute,
    # rule or schedule that applies, and a deployment must replace these defaults with figures that the law supports.
    # Set to 0 to leave the amount to the issuing authority.
    civic_challan_min_inr: int = 10_000
    departmental_fine_min_inr: int = 1_000_000


def get_settings() -> Settings:
    return Settings(
        env=os.getenv("APN_ENV", ""),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./case_core.db"),
        response_window_days=int(os.getenv("APN_RESPONSE_WINDOW_DAYS", "10")),
        decision_sla_hours=int(os.getenv("APN_DECISION_SLA_HOURS", "24")),
        checkpoint_key=os.getenv("APN_CHECKPOINT_KEY", ""),
        cors_origins=tuple(o.strip() for o in os.getenv("APN_CORS_ORIGINS", "").split(",") if o.strip()),
        civic_challan_min_inr=int(os.getenv("APN_CIVIC_CHALLAN_MIN_INR", "10000")),
        departmental_fine_min_inr=int(os.getenv("APN_DEPARTMENTAL_FINE_MIN_INR", "1000000")),
    )
