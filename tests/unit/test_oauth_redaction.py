from transcendence_memory.backend.auth.models import OAuthTokenState


def test_oauth_redaction_masks_tokens() -> None:
    state = OAuthTokenState(
        access_token="access-secret",
        refresh_token="refresh-secret",
        token_type="Bearer",
        subject="user-123",
    )
    redacted = state.redacted()
    assert redacted.access_token == "***"
    assert redacted.refresh_token == "***"
    assert redacted.subject == "user-123"
