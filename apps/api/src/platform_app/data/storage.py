"""Verwendeter Speicherport; der erste Adapter ist atomar mit Metadaten und Audit."""

from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from platform_app.data.engine import MAX_RESULT_BYTES, DataError, digest
from platform_app.data.models import DataBlob


class BlobStore(Protocol):
    def put(self, content: bytes) -> tuple[UUID, str]: ...
    def get(self, blob_id: UUID) -> bytes: ...


class PostgresBlobStore:
    def __init__(self, db: Session, organization_id: UUID):
        self.db = db
        self.organization_id = organization_id

    def put(self, content: bytes) -> tuple[UUID, str]:
        if not 0 < len(content) <= MAX_RESULT_BYTES:
            raise DataError("Das Speicherobjekt überschreitet die zulässige Größe.")
        blob = DataBlob(
            organization_id=self.organization_id, content=content, content_hash=digest(content)
        )
        self.db.add(blob)
        self.db.flush()
        return blob.id, blob.content_hash

    def get(self, blob_id: UUID) -> bytes:
        blob = self.db.get(DataBlob, blob_id)
        if blob is None or blob.organization_id != self.organization_id:
            raise DataError("Das Speicherobjekt ist nicht verfügbar.")
        if blob.content is None:
            raise DataError("Große Speicherobjekte müssen abschnittsweise gelesen werden.")
        if digest(blob.content) != blob.content_hash:
            raise DataError("Die Integritätsprüfung des Speicherobjekts ist fehlgeschlagen.")
        return blob.content
