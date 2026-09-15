"""Audit und Fachänderung verwenden dieselbe Transaktion."""

from typing import Any, Protocol
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from platform_app.shared.context import request_id


class Actor(Protocol):
    @property
    def user_id(self) -> UUID: ...
    @property
    def organization_id(self) -> UUID: ...


def append_audit(
    session: Session,
    actor: Actor,
    event_type: str,
    entity_type: str,
    entity_id: UUID | None,
    metadata: dict[str, Any],
) -> None:
    from platform_app.assessments.models import AuditEvent

    session.add(
        AuditEvent(
            organization_id=actor.organization_id,
            actor_user_id=actor.user_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            event_metadata=metadata,
            request_id=request_id.get() or uuid4(),
        )
    )
