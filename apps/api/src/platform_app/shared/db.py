"""Getrennte DB-Rollen und transaktionslokaler Mandantenkontext."""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from uuid import UUID

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session

from platform_app.shared.config import get_settings


class Base(DeclarativeBase):
    pass


@lru_cache
def engine_for(kind: str = "app") -> Engine:
    if os.environ.get("DATA_WORKER_MODE") == "true":
        if kind != "app":
            raise ValueError("Der Datenworker besitzt ausschließlich Anwendungszugang.")
        url = os.environ["DATABASE_URL"]
    else:
        settings = get_settings()
        url = {
            "app": settings.database_url,
            "auth": settings.auth_database_url,
            "migration": settings.migration_database_url,
        }[kind]
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=5,
        connect_args={"connect_timeout": 5},
        pool_reset_on_return="rollback",
        hide_parameters=True,
    )


@contextmanager
def auth_session() -> Iterator[Session]:
    with Session(engine_for("auth"), expire_on_commit=False) as session, session.begin():
        yield session


@contextmanager
def tenant_session(organization_id: UUID) -> Iterator[Session]:
    if not isinstance(organization_id, UUID):
        raise ValueError("Ein bestätigter Mandantenkontext ist erforderlich.")
    with Session(engine_for(), expire_on_commit=False) as session, session.begin():
        session.execute(
            text(
                "SELECT set_config('app.organization_id', :org, true), set_config('statement_timeout', '5s', true)"
            ),
            {"org": str(organization_id)},
        )
        yield session
