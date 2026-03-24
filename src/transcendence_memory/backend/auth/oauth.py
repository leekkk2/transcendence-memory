from __future__ import annotations

import base64
import hashlib
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlencode, urlparse

import httpx

from .models import OAuthTokenState
from ..settings import OAuthClientConfig


def generate_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    return verifier, challenge


def build_authorization_url(
    oauth: OAuthClientConfig,
    *,
    redirect_uri: str,
    state: str,
    code_challenge: str,
) -> str:
    base = oauth.authorize_url or f"{oauth.issuer.rstrip('/')}/authorize"
    query = urlencode(
        {
            "response_type": "code",
            "client_id": oauth.client_id or "",
            "redirect_uri": redirect_uri,
            "scope": " ".join(oauth.scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{base}?{query}"


def wait_for_loopback_code(host: str, port: int, expected_state: str) -> str:
    result: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            parsed = urlparse(self.path)
            params = dict(item.split("=", 1) for item in parsed.query.split("&") if "=" in item)
            if params.get("state") != expected_state:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"State mismatch")
                return
            result["code"] = params.get("code", "")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Transcendence Memory login completed. You can close this window.")

        def log_message(self, format, *args):  # noqa: A003
            return

    server = HTTPServer((host, port), Handler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    thread.join(timeout=120)
    server.server_close()
    return result["code"]


def exchange_code_for_token(
    oauth: OAuthClientConfig,
    *,
    code: str,
    verifier: str,
    redirect_uri: str,
) -> OAuthTokenState:
    token_url = oauth.token_url or f"{oauth.issuer.rstrip('/')}/token"
    response = httpx.post(
        token_url,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": oauth.client_id or "",
            "code_verifier": verifier,
        },
        timeout=30.0,
    )
    response.raise_for_status()
    payload = response.json()
    return OAuthTokenState(
        access_token=payload.get("access_token"),
        refresh_token=payload.get("refresh_token"),
        token_type=payload.get("token_type", "Bearer"),
        expires_at=payload.get("expires_at"),
        subject=payload.get("sub") or payload.get("subject"),
    )


def login_via_browser(oauth: OAuthClientConfig) -> OAuthTokenState:
    verifier, challenge = generate_pkce_pair()
    state = secrets.token_urlsafe(16)
    redirect_uri = f"http://{oauth.redirect_host}:{oauth.redirect_port}/callback"
    authorization_url = build_authorization_url(
        oauth,
        redirect_uri=redirect_uri,
        state=state,
        code_challenge=challenge,
    )
    webbrowser.open(authorization_url)
    code = wait_for_loopback_code(oauth.redirect_host, oauth.redirect_port, state)
    return exchange_code_for_token(oauth, code=code, verifier=verifier, redirect_uri=redirect_uri)
