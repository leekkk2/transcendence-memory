from __future__ import annotations

from .models import APIKeyAuthConfig, AuthStatus


def header_name() -> str:
    return APIKeyAuthConfig().header_name


def auth_status_from_runtime(runtime) -> AuthStatus:
    secrets = runtime.bootstrap_secrets
    return AuthStatus(
        auth_mode=runtime.settings.auth_mode,
        api_key_configured=bool(secrets and secrets.api_key),
        access_token_present=bool(secrets and getattr(secrets, "oauth_access_token", None)),
        refresh_token_present=bool(secrets and getattr(secrets, "oauth_refresh_token", None)),
        token_type=getattr(secrets, "oauth_token_type", None),
        subject=getattr(secrets, "oauth_subject", None) or ("local-operator" if secrets and secrets.api_key else None),
    )


def validate_api_key(candidate: str | None, runtime) -> bool:
    if not candidate:
        return False
    secrets = runtime.bootstrap_secrets
    return bool(secrets and secrets.api_key and candidate == secrets.api_key)


def validate_bearer_token(candidate: str | None, runtime) -> bool:
    if not candidate:
        return False
    secrets = runtime.bootstrap_secrets
    token = getattr(secrets, "oauth_access_token", None) if secrets else None
    return bool(token and candidate == token)
