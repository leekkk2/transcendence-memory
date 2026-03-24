from __future__ import annotations

from fastapi import APIRouter, Request

from ....deploy.health import classify_runtime_health

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
def health(request: Request) -> dict[str, object]:
    runtime = request.app.state.runtime_config
    summary = classify_runtime_health(runtime, deployment_mode="api")
    return {
        "status": summary["status"],
        "service": "transcendence-memory-backend",
        "auth_mode": runtime.settings.auth_mode,
        "provider": runtime.settings.provider,
        "database": summary["database"],
        "provider_config": summary["provider_config"],
        "deployment": summary["deployment"],
    }
