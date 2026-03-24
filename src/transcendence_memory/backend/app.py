from __future__ import annotations

from fastapi import FastAPI

from .settings import load_runtime_config


def create_app() -> FastAPI:
    runtime = load_runtime_config()
    app = FastAPI(
        title="Transcendence Memory Backend",
        version="0.1.0",
        description="Authenticated backend runtime for Transcendence Memory.",
    )
    app.state.runtime_config = runtime
    return app


app = create_app()
