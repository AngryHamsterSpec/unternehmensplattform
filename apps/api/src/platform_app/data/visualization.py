"""Begrenzte, reproduzierbare Diagrammauswahl aus unveränderten Datenversionen."""

import json
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text

from platform_app.data.engine import decode_table, digest
from platform_app.data.models import DataBlob
from platform_app.data.schemas import ChartRow, ChartSample
from platform_app.data.service import version_for
from platform_app.data.storage import PostgresBlobStore
from platform_app.identity.dependencies import ActorContext
from platform_app.shared.db import tenant_session

MAX_POINTS = 300
MAX_CHUNKS = 12


def spread_indices(size: int, limit: int) -> list[int]:
    """Gleichmäßige Positionen einschließlich Anfang/Ende; keine Zufallsstichprobe."""
    count = min(size, limit)
    if count < 2:
        return list(range(count))
    return [i * (size - 1) // (count - 1) for i in range(count)]


def chart_sample(
    actor: ActorContext, dataset_id: UUID, version_no: int, x: int, y: int
) -> ChartSample:
    with tenant_session(actor.organization_id) as db:
        version = version_for(db, dataset_id, version_no)
        columns = [column["name"] for column in version.profile["columns"]]
        if max(x, y) >= len(columns):
            raise HTTPException(422, "Die ausgewählte Diagrammspalte existiert nicht.")
        total = int(version.profile["rows"])
        content_hash = version.content_hash
        blob = db.get(DataBlob, version.blob_id)
        if blob is None:
            raise HTTPException(404, "Die Datenversion ist nicht verfügbar.")
        object_id = blob.object_id
        inline = None
        chunks: list[tuple[int, int, int]] = []
        if object_id is None:
            inline = decode_table(PostgresBlobStore(db, actor.organization_id).get(blob.id))
        else:
            records = db.execute(
                text(
                    "SELECT ordinal,row_start,row_count FROM data_chunks "
                    "WHERE object_id=:id AND row_count>0 ORDER BY ordinal"
                ),
                {"id": object_id},
            ).all()
            chunks = [(int(r[0]), int(r[1]), int(r[2])) for r in records]
    points: list[ChartRow] = []
    truncated = 0

    def append(row_number: int, values: list[str]) -> None:
        nonlocal truncated
        selected = [values[x], values[y]]
        truncated += sum(len(value) > 512 for value in selected)
        points.append(ChartRow(row_number=row_number, values=[v[:512] for v in selected]))

    if inline is not None:
        for index in spread_indices(len(inline.rows), MAX_POINTS):
            append(index + 1, inline.rows[index])
    elif chunks:
        chosen = [chunks[index] for index in spread_indices(len(chunks), MAX_CHUNKS)]
        per_chunk = MAX_POINTS // len(chosen)
        for ordinal, row_start, row_count in chosen:
            # Höchstens zwölf Abschnitte; jede kurze Transaktion behält RLS bei.
            with tenant_session(actor.organization_id) as db:
                chunk = db.execute(
                    text(
                        "SELECT content,content_hash FROM data_chunks "
                        "WHERE object_id=:id AND ordinal=:ordinal"
                    ),
                    {"id": object_id, "ordinal": ordinal},
                ).one()
                content = bytes(chunk[0])
                if digest(content) != chunk[1]:
                    raise HTTPException(
                        409, "Die Integritätsprüfung der Diagrammdaten ist fehlgeschlagen."
                    )
            lines = content.splitlines()
            first = 1 if row_start == 0 else 0
            for index in spread_indices(row_count - first, per_chunk):
                local = first + index
                append(row_start + local, json.loads(lines[local]))
    return ChartSample(
        version_no=version_no,
        content_hash=content_hash,
        total_rows=total,
        columns=[columns[x], columns[y]],
        rows=points,
        method="complete" if len(points) == total else "systematic-chunks-v1",
        truncated_cells=truncated,
    )
