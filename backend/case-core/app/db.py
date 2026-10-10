from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .models import Base

# The ledger rejects UPDATE and DELETE at the database level. A determined administrator with schema access can
# drop these triggers, which is why the ledger is also hash-chained and can be verified and checkpointed externally.
SQLITE_LEDGER_TRIGGERS = (
    """CREATE TRIGGER IF NOT EXISTS ledger_no_update BEFORE UPDATE ON ledger
       BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END""",
    """CREATE TRIGGER IF NOT EXISTS ledger_no_delete BEFORE DELETE ON ledger
       BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END""",
)


def make_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        kwargs: dict = {"connect_args": {"check_same_thread": False}}
        if ":memory:" in url or url in ("sqlite://", "sqlite:///"):
            kwargs["poolclass"] = StaticPool
        return create_engine(url, **kwargs)
    return create_engine(url)


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    if engine.dialect.name == "sqlite":
        with engine.begin() as conn:
            for ddl in SQLITE_LEDGER_TRIGGERS:
                conn.execute(text(ddl))


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)


def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
    finally:
        session.close()
