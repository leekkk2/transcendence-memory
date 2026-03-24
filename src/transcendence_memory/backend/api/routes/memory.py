from __future__ import annotations

from contextlib import contextmanager

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from ...auth.dependencies import require_auth
from ...db.session import create_session_factory
from ...services.memory import embed_content, search_content

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])


class EmbedRequest(BaseModel):
    content: str
    metadata: dict = Field(default_factory=dict)


class SearchRequest(BaseModel):
    query: str
    limit: int = 5


@contextmanager
def _session_scope(request: Request):
    runtime = request.app.state.runtime_config
    factory = create_session_factory(runtime.settings)
    session = factory()
    try:
        yield session
    finally:
        session.close()


@router.post("/embed")
def embed_memory(
    payload: EmbedRequest,
    request: Request,
    _auth: dict = Depends(require_auth),
) -> dict[str, object]:
    runtime = request.app.state.runtime_config
    with _session_scope(request) as session:
        record = embed_content(runtime, session, content=payload.content, metadata=payload.metadata)
    return {
        "id": record.id,
        "provider": record.provider,
        "model": record.model,
        "metadata": record.metadata_json,
        "vector_dimension": len(record.embedding),
    }


@router.post("/search")
def search_memory(
    payload: SearchRequest,
    request: Request,
    _auth: dict = Depends(require_auth),
) -> dict[str, object]:
    runtime = request.app.state.runtime_config
    with _session_scope(request) as session:
        results = search_content(runtime, session, query=payload.query, limit=payload.limit)
    return {
        "results": results,
        "count": len(results),
    }
