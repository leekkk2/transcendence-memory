from __future__ import annotations

from typing import Any

import httpx

from ..settings import LoadedRuntimeConfig


def _auth_header(runtime: LoadedRuntimeConfig) -> dict[str, str]:
    secrets = runtime.bootstrap_secrets
    if secrets and secrets.api_key:
        return {"Authorization": f"Bearer {secrets.api_key}"}
    if secrets and secrets.oauth_access_token:
        return {"Authorization": f"Bearer {secrets.oauth_access_token}"}
    return {}


def generate_embedding(runtime: LoadedRuntimeConfig, text: str) -> list[float]:
    base_url = runtime.settings.provider_base_url.rstrip("/")
    response = httpx.post(
        f"{base_url}/embeddings",
        headers=_auth_header(runtime),
        json={
            "model": runtime.settings.model,
            "input": text,
        },
        timeout=30.0,
    )
    response.raise_for_status()
    payload: dict[str, Any] = response.json()
    data = payload.get("data", [])
    if not data:
        raise ValueError("Embedding provider returned no vector data.")
    return data[0]["embedding"]
