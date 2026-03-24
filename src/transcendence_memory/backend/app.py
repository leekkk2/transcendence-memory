from __future__ import annotations

from fastapi import FastAPI

from .api.routes.auth import router as auth_router
from .api.routes.health import router as health_router
from .settings import load_runtime_config


def create_app() -> FastAPI:
    runtime = load_runtime_config()
    app = FastAPI(
        title="Transcendence Memory Backend",
        version="0.1.0",
        description="Authenticated backend runtime for Transcendence Memory.",
    )
    app.state.runtime_config = runtime
    app.include_router(health_router)
    app.include_router(auth_router)
    return app


app = create_app()
