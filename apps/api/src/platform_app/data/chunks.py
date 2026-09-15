"""Mandantengebundene, unveränderliche Speicherabschnitte mit begrenztem RAM."""

import hashlib
import json
from collections.abc import Iterator
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from platform_app.data.engine import DataError, digest
from platform_app.data.models import DataBlob
from platform_app.identity.dependencies import ActorContext
from platform_app.shared.authorization import check_write
from platform_app.shared.db import tenant_session

CHUNK_BYTES = 4 * 1024 * 1024
MAX_UPLOAD_BYTES = 1024**3
MAX_OBJECT_BYTES = 8 * MAX_UPLOAD_BYTES
ORG_STORAGE_BYTES = 20 * MAX_UPLOAD_BYTES


def object_for(db: Session, object_id: UUID, *, lock: bool = False) -> dict[str, Any]:
    row = (
        db.execute(
            text("SELECT * FROM data_objects WHERE id=:id" + (" FOR UPDATE" if lock else "")),
            {"id": object_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise HTTPException(404, "Der Upload wurde nicht gefunden.")
    return dict(row)


def new_object(
    db: Session,
    actor: ActorContext,
    kind: str,
    expected: int = 0,
    metadata: dict[str, Any] | None = None,
) -> UUID:
    reserved = (
        db.scalar(
            text(
                "SELECT coalesce(sum(greatest(received_bytes,expected_bytes)),0) FROM data_objects WHERE status!='CANCELLED'"
            )
        )
        or 0
    )
    if reserved + expected > ORG_STORAGE_BYTES:
        raise HTTPException(409, "Die Speichergrenze von 20 GiB je Organisation ist erreicht.")
    oid = uuid4()
    db.execute(
        text(
            "INSERT INTO data_objects(id,organization_id,created_by_user_id,kind,expected_bytes,metadata) VALUES(:id,:org,:user,:kind,:size,CAST(:meta AS jsonb))"
        ),
        {
            "id": oid,
            "org": actor.organization_id,
            "user": actor.user_id,
            "kind": kind,
            "size": expected,
            "meta": json.dumps(metadata or {}),
        },
    )
    return oid


def append_chunk(
    actor: ActorContext,
    oid: UUID,
    ordinal: int,
    content: bytes,
    row_start: int | None = None,
    row_count: int | None = None,
) -> dict[str, Any]:
    if not 0 < len(content) <= CHUNK_BYTES:
        raise HTTPException(413, "Ein Dateiabschnitt muss zwischen 1 Byte und 4 MiB groß sein.")
    content_hash = digest(content)
    with tenant_session(actor.organization_id) as db:
        check_write(db, actor)
        obj = object_for(db, oid, lock=True)
        if obj["status"] != "OPEN":
            raise HTTPException(409, "Dieser Upload ist bereits abgeschlossen oder abgebrochen.")
        if ordinal < obj["chunk_count"]:
            old = db.scalar(
                text("SELECT content_hash FROM data_chunks WHERE object_id=:id AND ordinal=:n"),
                {"id": oid, "n": ordinal},
            )
            if old == content_hash:
                return obj
            raise HTTPException(409, "Der bereits gespeicherte Abschnitt hat einen anderen Inhalt.")
        if ordinal != obj["chunk_count"]:
            raise HTTPException(409, "Die Reihenfolge der Dateiabschnitte stimmt nicht.")
        if obj["chunk_count"] >= (1024 if obj["kind"] == "UPLOAD" else 4096):
            raise HTTPException(
                413, "Zu viele Dateiabschnitte. Bitte Abschnitte bis 4 MiB verwenden."
            )
        total = obj["received_bytes"] + len(content)
        limit = obj["expected_bytes"] if obj["kind"] == "UPLOAD" else MAX_OBJECT_BYTES
        if total > limit:
            raise HTTPException(
                413, "Die deklarierte Dateigröße oder Speichergrenze ist überschritten."
            )
        reserved = (
            db.scalar(
                text(
                    "SELECT coalesce(sum(greatest(received_bytes,expected_bytes)),0) FROM data_objects WHERE status!='CANCELLED'"
                )
            )
            or 0
        )
        extra = max(total, obj["expected_bytes"]) - max(
            obj["received_bytes"], obj["expected_bytes"]
        )
        if reserved + extra > ORG_STORAGE_BYTES:
            raise HTTPException(409, "Die Speichergrenze von 20 GiB je Organisation ist erreicht.")
        db.execute(
            text(
                "INSERT INTO data_chunks(organization_id,object_id,ordinal,content,content_hash,row_start,row_count) VALUES(:org,:id,:n,:data,:hash,:start,:rows)"
            ),
            {
                "org": actor.organization_id,
                "id": oid,
                "n": ordinal,
                "data": content,
                "hash": content_hash,
                "start": row_start,
                "rows": row_count,
            },
        )
        db.execute(
            text(
                "UPDATE data_objects SET received_bytes=:size,chunk_count=chunk_count+1 WHERE id=:id"
            ),
            {"id": oid, "size": total},
        )
        return {**obj, "received_bytes": total, "chunk_count": ordinal + 1}


def iter_object(org: UUID, oid: UUID, count: int) -> Iterator[bytes]:
    for ordinal in range(count):
        with tenant_session(org) as db:
            row = db.execute(
                text(
                    "SELECT content,content_hash FROM data_chunks WHERE object_id=:id AND ordinal=:n"
                ),
                {"id": oid, "n": ordinal},
            ).first()
            if row is None:
                raise DataError("Ein Speicherabschnitt ist nicht verfügbar.")
            content, expected_hash = bytes(row[0]), row[1]
        if digest(content) != expected_hash:
            raise DataError("Die Integritätsprüfung eines Speicherabschnitts ist fehlgeschlagen.")
        yield content


def hash_object(org: UUID, oid: UUID, count: int) -> str:
    value = hashlib.sha256()
    for chunk in iter_object(org, oid, count):
        value.update(chunk)
    return value.hexdigest()


def seal_blob(
    db: Session,
    actor: ActorContext,
    oid: UUID,
    content_hash: str,
    metadata: dict[str, Any] | None = None,
) -> DataBlob:
    obj = object_for(db, oid, lock=True)
    if obj["status"] != "OPEN":
        raise HTTPException(409, "Das Speicherobjekt ist bereits abgeschlossen.")
    db.execute(
        text("UPDATE data_objects SET status='SEALED',content_hash=:hash WHERE id=:id"),
        {"id": oid, "hash": content_hash},
    )
    blob = DataBlob(
        organization_id=actor.organization_id,
        content=None,
        object_id=oid,
        content_hash=content_hash,
        storage_meta=metadata or {},
    )
    db.add(blob)
    db.flush()
    return blob


def cancel_object(db: Session, oid: UUID) -> None:
    obj = object_for(db, oid, lock=True)
    if obj["status"] == "CANCELLED":
        return
    if obj["status"] != "OPEN":
        raise HTTPException(409, "Abgeschlossene Originale können nicht abgebrochen werden.")
    db.execute(text("DELETE FROM data_chunks WHERE object_id=:id"), {"id": oid})
    db.execute(
        text(
            "UPDATE data_objects SET status='CANCELLED',received_bytes=0,chunk_count=0 WHERE id=:id"
        ),
        {"id": oid},
    )


def blob_info(db: Session, blob_id: UUID) -> tuple[DataBlob, dict[str, Any]]:
    blob = db.get(DataBlob, blob_id)
    if blob is None or blob.object_id is None:
        raise DataError("Das abschnittsweise Speicherobjekt wurde nicht gefunden.")
    return blob, object_for(db, blob.object_id)
