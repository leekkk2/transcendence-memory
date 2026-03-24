from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import MemoryRecord
from .embeddings import generate_embedding


def embed_content(
    runtime,
    session: Session,
    *,
    content: str,
    metadata: dict | None = None,
) -> MemoryRecord:
    vector = generate_embedding(runtime, content)
    record = MemoryRecord(
        content=content,
        metadata_json=metadata or {},
        embedding=vector,
        provider=runtime.settings.provider,
        model=runtime.settings.model,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def search_content(
    runtime,
    session: Session,
    *,
    query: str,
    limit: int = 5,
) -> list[dict]:
    vector = generate_embedding(runtime, query)
    stmt = (
        select(MemoryRecord, MemoryRecord.embedding.cosine_distance(vector).label("score"))
        .order_by("score")
        .limit(limit)
    )
    rows = session.execute(stmt).all()
    return [
        {
            "id": row.MemoryRecord.id,
            "content": row.MemoryRecord.content,
            "metadata": row.MemoryRecord.metadata_json,
            "provider": row.MemoryRecord.provider,
            "model": row.MemoryRecord.model,
            "score": float(row.score),
        }
        for row in rows
    ]
