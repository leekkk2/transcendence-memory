from __future__ import annotations

from pathlib import Path

from transcendence_memory.bootstrap.paths import ResolvedPaths
from transcendence_memory.bootstrap.persistence import update_connection_bundle_config
from transcendence_memory.handoff.models import ConnectionBundle


def load_bundle_from_input(
    *,
    bundle_file: Path | None = None,
    bundle_json: str | None = None,
) -> ConnectionBundle:
    if bundle_file is None and bundle_json is None:
        raise ValueError("Provide either --bundle-file or --bundle-json.")
    if bundle_file is not None and bundle_json is not None:
        raise ValueError("Provide only one of --bundle-file or --bundle-json.")
    raw = bundle_file.read_text(encoding="utf-8") if bundle_file is not None else bundle_json
    return ConnectionBundle.model_validate_json(raw or "")


def import_connection_bundle(paths: ResolvedPaths, bundle: ConnectionBundle):
    return update_connection_bundle_config(
        paths,
        topology=bundle.topology,
        auth_mode=bundle.auth.mode,
        provider=bundle.provider.provider,
        model=bundle.provider.model,
        provider_base_url=bundle.provider.base_url,
        advertised_url=bundle.backend.advertised_url,
        health_path=bundle.backend.health_path,
        embed_path=bundle.backend.embed_path,
        search_path=bundle.backend.search_path,
        bundle_version=bundle.bundle_version,
        required_local_inputs=bundle.auth.required_local_inputs,
    )


def missing_local_inputs(runtime) -> list[str]:
    config = runtime.bootstrap_config
    secrets = runtime.bootstrap_secrets
    if config is None:
        return ["connection_bundle"]
    missing: list[str] = []
    for item in config.required_local_inputs:
        if item == "api_key" and not (secrets and secrets.api_key):
            missing.append(item)
        if item == "oauth_login" and not (secrets and secrets.oauth_access_token):
            missing.append(item)
    return missing
