from __future__ import annotations

from transcendence_memory.backend.auth.models import OAuthTokenState
from transcendence_memory.bootstrap.models import BootstrapSecrets
from transcendence_memory.bootstrap.paths import ResolvedPaths
from transcendence_memory.bootstrap.persistence import read_secrets, write_secrets


def load_token_state(paths: ResolvedPaths) -> OAuthTokenState:
    secrets = read_secrets(paths) or BootstrapSecrets()
    return OAuthTokenState(
        access_token=secrets.oauth_access_token,
        refresh_token=secrets.oauth_refresh_token,
        token_type=secrets.oauth_token_type or "Bearer",
        expires_at=secrets.oauth_expires_at,
        subject=secrets.oauth_subject,
    )


def store_token_state(paths: ResolvedPaths, token_state: OAuthTokenState) -> None:
    secrets = read_secrets(paths) or BootstrapSecrets()
    secrets.oauth_access_token = token_state.access_token
    secrets.oauth_refresh_token = token_state.refresh_token
    secrets.oauth_token_type = token_state.token_type
    secrets.oauth_expires_at = token_state.expires_at
    secrets.oauth_subject = token_state.subject
    write_secrets(secrets, paths)


def clear_token_state(paths: ResolvedPaths) -> None:
    secrets = read_secrets(paths) or BootstrapSecrets()
    secrets.oauth_access_token = None
    secrets.oauth_refresh_token = None
    secrets.oauth_token_type = None
    secrets.oauth_expires_at = None
    secrets.oauth_subject = None
    write_secrets(secrets, paths)
