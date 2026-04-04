from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field

from transcendence_memory.bootstrap.models import BootstrapConfig, BootstrapSecrets
from transcendence_memory.bootstrap.paths import ResolvedPaths, resolve_paths
from transcendence_memory.bootstrap.persistence import read_config, read_secrets


class OAuthClientConfig(BaseModel):
    issuer: str | None = None
    authorize_url: str | None = None
    token_url: str | None = None
    client_id: str | None = None
    scopes: list[str] = Field(default_factory=lambda: ["openid", "profile", "email"])
    redirect_host: str = "127.0.0.1"
    redirect_port: int = 8765


class BackendSettings(BaseModel):
    bind_host: str = "127.0.0.1"
    bind_port: int = 8711
    advertised_url: str = "http://127.0.0.1:8711"
    health_path: str = "/api/v1/health"
    embed_path: str = "/api/v1/memory/embed"
    search_path: str = "/api/v1/memory/search"
    auth_mode: str = "api_key"
    provider: str = "openai"
    model: str = "text-embedding-3-small"
    provider_base_url: str = "https://api.openai.com/v1"
    oauth: OAuthClientConfig = Field(default_factory=OAuthClientConfig)
    config_path: str
    secret_path: str


class AuthState(BaseModel):
    auth_mode: str = "api_key"
    api_key_configured: bool = False
    access_token_present: bool = False
    refresh_token_present: bool = False
    token_type: str | None = None
    subject: str | None = None


@dataclass
class LoadedRuntimeConfig:
    paths: ResolvedPaths
    bootstrap_config: BootstrapConfig | None
    bootstrap_secrets: BootstrapSecrets | None
    settings: BackendSettings


def _default_oauth_from_base(base_url: str | None) -> OAuthClientConfig:
    if not base_url:
        return OAuthClientConfig()
    trimmed = base_url.rstrip("/")
    return OAuthClientConfig(
        issuer=trimmed,
        authorize_url=f"{trimmed}/authorize",
        token_url=f"{trimmed}/token",
    )


def load_runtime_config(
    config_path: str | Path | None = None,
    secret_path: str | Path | None = None,
) -> LoadedRuntimeConfig:
    paths = resolve_paths(config_path=config_path, secret_path=secret_path)
    bootstrap_config = read_config(paths)
    bootstrap_secrets = read_secrets(paths)

    if bootstrap_config is None:
        inferred_auth_mode = "api_key"
        if bootstrap_secrets and bootstrap_secrets.oauth_access_token:
            inferred_auth_mode = "oauth"
        settings = BackendSettings(
            auth_mode=inferred_auth_mode,
            config_path=str(paths.config_root),
            secret_path=str(paths.secret_root),
        )
        return LoadedRuntimeConfig(paths=paths, bootstrap_config=None, bootstrap_secrets=bootstrap_secrets, settings=settings)

    oauth = _default_oauth_from_base(bootstrap_config.base_url)
    settings = BackendSettings(
        provider=bootstrap_config.provider,
        model=bootstrap_config.model,
        provider_base_url=bootstrap_config.base_url or "https://api.openai.com/v1",
        advertised_url=bootstrap_config.advertised_url or "http://127.0.0.1:8711",
        health_path=bootstrap_config.health_path,
        embed_path=bootstrap_config.embed_path,
        search_path=bootstrap_config.search_path,
        auth_mode=bootstrap_config.auth_mode if bootstrap_config.auth_mode else ("oauth" if bootstrap_secrets and bootstrap_secrets.oauth_access_token else "api_key"),
        oauth=OAuthClientConfig(
            issuer=bootstrap_config.oauth_issuer or oauth.issuer,
            authorize_url=bootstrap_config.oauth_authorize_url or oauth.authorize_url,
            token_url=bootstrap_config.oauth_token_url or oauth.token_url,
            client_id=bootstrap_config.oauth_client_id,
            scopes=bootstrap_config.oauth_scopes,
        ),
        config_path=str(paths.config_root),
        secret_path=str(paths.secret_root),
    )
    return LoadedRuntimeConfig(
        paths=paths,
        bootstrap_config=bootstrap_config,
        bootstrap_secrets=bootstrap_secrets,
        settings=settings,
    )
