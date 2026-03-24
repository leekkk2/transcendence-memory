from __future__ import annotations

from fastapi import APIRouter, Request

from ...auth.api_keys import auth_status_from_runtime

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/status")
def auth_status(request: Request) -> dict[str, object]:
    runtime = request.app.state.runtime_config
    return auth_status_from_runtime(runtime).model_dump(mode="json")
