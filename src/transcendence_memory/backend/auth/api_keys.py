from __future__ import annotations

from .models import APIKeyAuthConfig, AuthStatus


def header_name() -> str:
    return APIKeyAuthConfig().header_name


def auth_status_from_runtime(runtime) -> AuthStatus:
    secrets = runtime.bootstrap_secrets
    return AuthStatus(
        auth_mode=runtime.settings.auth_mode,
        api_key_configured=bool(secrets and secrets.api_key),
        access_token_present=False,
        refresh_token_present=False,
        token_type=None,
        subject="local-operator" if secrets and secrets.api_key else None,
    )


def validate_api_key(candidate: str | None, runtime) -> bool:
    if not candidate:
        return False
    secrets = runtime.bootstrap_secrets
    return bool(secrets and secrets.api_key and candidate == secrets.api_key)
