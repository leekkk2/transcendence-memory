from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
def health(request: Request) -> dict[str, object]:
    runtime = request.app.state.runtime_config
    return {
        "status": "ok",
        "service": "transcendence-memory-backend",
        "auth_mode": runtime.settings.auth_mode,
        "provider": runtime.settings.provider,
    }
