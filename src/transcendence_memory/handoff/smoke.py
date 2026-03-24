from __future__ import annotations

from typing import Any

import httpx

from transcendence_memory.handoff.importer import missing_local_inputs


def _auth_headers(runtime) -> dict[str, str]:
    secrets = runtime.bootstrap_secrets
    if runtime.settings.auth_mode == "oauth" and secrets and secrets.oauth_access_token:
        return {"Authorization": f"Bearer {secrets.oauth_access_token}"}
    if secrets and secrets.api_key:
        return {"X-Transcendence-API-Key": secrets.api_key}
    return {}


def run_smoke_checks(runtime, *, text: str = "transcendence smoke sample") -> dict[str, Any]:
    missing = missing_local_inputs(runtime)
    if missing:
        raise ValueError(f"Missing local inputs: {', '.join(missing)}")

    base = runtime.settings.advertised_url.rstrip("/")
    headers = _auth_headers(runtime)

    health_response = httpx.get(f"{base}{runtime.settings.health_path}", timeout=5.0)
    health_response.raise_for_status()
    health_payload = health_response.json()

    embed_response = httpx.post(
        f"{base}{runtime.settings.embed_path}",
        headers=headers,
        json={"content": text, "metadata": {"source": "smoke"}},
        timeout=10.0,
    )
    embed_response.raise_for_status()
    embed_payload = embed_response.json()

    search_response = httpx.post(
        f"{base}{runtime.settings.search_path}",
        headers=headers,
        json={"query": text, "limit": 3},
        timeout=10.0,
    )
    search_response.raise_for_status()
    search_payload = search_response.json()

    return {
        "health": health_payload,
        "embed": embed_payload,
        "search": search_payload,
    }
