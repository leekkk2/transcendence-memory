from __future__ import annotations

import json
import os
import tomllib
from pathlib import Path

import tomli_w

from .models import (
    BootstrapConfig,
    BootstrapPlan,
    BootstrapSecrets,
    BootstrapSelection,
    BootstrapState,
    DetectionResult,
    ResolvedPaths,
)
from .paths import ensure_layout, ensure_secret_permissions


def _drop_none(value):
    if isinstance(value, dict):
        return {key: _drop_none(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [_drop_none(item) for item in value if item is not None]
    return value


def _write_toml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        tomli_w.dump(_drop_none(payload), handle)


def _read_toml(path: Path) -> dict | None:
    if not path.exists():
        return None
    with path.open("rb") as handle:
        return tomllib.load(handle)


def build_bootstrap_config(
    selection: BootstrapSelection,
    paths: ResolvedPaths,
    detection: DetectionResult,
) -> BootstrapConfig:
    deferred_items = list(selection.provider.base_url and [] or [])
    if selection.transport_hint.value == "ip_port":
        deferred_items.append(
            "Domain/reverse-proxy inputs were not provided; continue with IP + port and upgrade later."
        )
    return BootstrapConfig(
        role=selection.role,
        topology=selection.topology,
        transport_hint=selection.transport_hint,
        auth_mode="api_key",
        provider=selection.provider.provider,
        model=selection.provider.model,
        base_url=selection.provider.base_url or f"http://{detection.local_ip}:8000",
        config_path=str(paths.config_root),
        secret_path=str(paths.secret_root),
        deferred_items=deferred_items,
    )


def write_config(config: BootstrapConfig, paths: ResolvedPaths) -> None:
    ensure_layout(paths)
    _write_toml(paths.config_file, config.model_dump(mode="json"))


def read_config(paths: ResolvedPaths) -> BootstrapConfig | None:
    payload = _read_toml(paths.config_file)
    if payload is None:
        return None
    return BootstrapConfig.model_validate(payload)


def write_secrets(secrets: BootstrapSecrets, paths: ResolvedPaths) -> None:
    ensure_layout(paths)
    _write_toml(paths.secret_file, secrets.model_dump(mode="json"))
    ensure_secret_permissions(paths.secret_file)


def read_secrets(paths: ResolvedPaths) -> BootstrapSecrets | None:
    payload = _read_toml(paths.secret_file)
    if payload is None:
        return None
    return BootstrapSecrets.model_validate(payload)


def write_state(
    selection: BootstrapSelection,
    plan: BootstrapPlan,
    config: BootstrapConfig,
    paths: ResolvedPaths,
) -> None:
    ensure_layout(paths)
    state = BootstrapState(
        role=selection.role,
        topology=selection.topology,
        transport_hint=selection.transport_hint,
        recommendation_reason=selection.recommendation_reason,
        last_plan_summary={
            "warnings": plan.warnings,
            "deferred_items": plan.deferred_items,
            "diff_summary": plan.diff_summary,
        },
        last_config=config.model_dump(mode="json"),
    )
    paths.state_file.write_text(
        json.dumps(state.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )


def read_state(paths: ResolvedPaths) -> BootstrapState | None:
    if not paths.state_file.exists():
        return None
    payload = json.loads(paths.state_file.read_text(encoding="utf-8"))
    return BootstrapState.model_validate(payload)


def diff_config(current: BootstrapConfig | None, desired: BootstrapConfig) -> list[str]:
    if current is None:
        return [f"Create config file {desired.config_path}/config.toml"]

    diffs: list[str] = []
    current_payload = current.model_dump(mode="json")
    desired_payload = desired.model_dump(mode="json")
    for key, new_value in desired_payload.items():
        old_value = current_payload.get(key)
        if old_value != new_value:
            diffs.append(f"{key}: {old_value!r} -> {new_value!r}")
    return diffs or ["No non-secret config changes required."]


def regenerate_config_from_state(paths: ResolvedPaths) -> bool:
    state = read_state(paths)
    if state is None or not state.last_config:
        return False
    config = BootstrapConfig.model_validate(state.last_config)
    write_config(config, paths)
    return True


def secret_file_needs_permission_fix(paths: ResolvedPaths) -> bool:
    if os.name == "nt" or not paths.secret_file.exists():
        return False
    return oct(paths.secret_file.stat().st_mode & 0o777) != "0o600"


def update_bootstrap_auth_config(
    paths: ResolvedPaths,
    *,
    auth_mode: str,
    oauth_issuer: str | None = None,
    oauth_authorize_url: str | None = None,
    oauth_token_url: str | None = None,
    oauth_client_id: str | None = None,
    oauth_scopes: list[str] | None = None,
) -> BootstrapConfig | None:
    config = read_config(paths)
    if config is None:
        return None

    updated = config.model_copy(
        update={
            "auth_mode": auth_mode,
            "oauth_issuer": oauth_issuer,
            "oauth_authorize_url": oauth_authorize_url,
            "oauth_token_url": oauth_token_url,
            "oauth_client_id": oauth_client_id,
            "oauth_scopes": oauth_scopes or config.oauth_scopes,
        }
    )
    write_config(updated, paths)
    return updated
