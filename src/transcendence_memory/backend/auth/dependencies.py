from __future__ import annotations

from fastapi import Header, HTTPException, Request, status

from .api_keys import header_name, validate_api_key, validate_bearer_token


def require_auth(
    request: Request,
    x_transcendence_api_key: str | None = Header(default=None, alias="X-Transcendence-API-Key"),
    authorization: str | None = Header(default=None),
) -> dict[str, str]:
    runtime = request.app.state.runtime_config
    if validate_api_key(x_transcendence_api_key, runtime):
        return {"auth_mode": "api_key", "principal": "local-operator"}

    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and validate_bearer_token(token, runtime):
            return {"auth_mode": "oauth", "principal": "oauth-subject"}
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token.")

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Missing valid {header_name()} header.",
    )
