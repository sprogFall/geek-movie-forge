from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from packages.db.models import Base


def create_database_engine(*, db_backend: str, database_url: str) -> Engine:
    kwargs: dict[str, object] = {"future": True}
    if db_backend == "sqlite":
        kwargs["connect_args"] = {"check_same_thread": False}
        if database_url.endswith("/:memory:"):
            kwargs["poolclass"] = StaticPool
    return create_engine(database_url, **kwargs)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def initialize_database(engine: Engine) -> None:
    Base.metadata.create_all(engine)
