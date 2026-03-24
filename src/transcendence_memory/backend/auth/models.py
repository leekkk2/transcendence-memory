from __future__ import annotations

from pydantic import BaseModel, Field


class APIKeyAuthConfig(BaseModel):
    header_name: str = "X-Transcendence-API-Key"
    configured: bool = False


class OAuthTokenState(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "Bearer"
    expires_at: int | None = None
    subject: str | None = None

    def redacted(self) -> "OAuthTokenState":
        return OAuthTokenState(
            access_token="***" if self.access_token else None,
            refresh_token="***" if self.refresh_token else None,
            token_type=self.token_type,
            expires_at=self.expires_at,
            subject=self.subject,
        )


class AuthStatus(BaseModel):
    auth_mode: str
    api_key_configured: bool
    access_token_present: bool
    refresh_token_present: bool
    token_type: str | None = None
    subject: str | None = None


class AuthContext(BaseModel):
    principal: str = "local-operator"
    auth_mode: str = "api_key"
    metadata: dict[str, str] = Field(default_factory=dict)
