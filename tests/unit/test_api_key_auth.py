from types import SimpleNamespace

from transcendence_memory.backend.auth.api_keys import auth_status_from_runtime, validate_api_key
from transcendence_memory.bootstrap.models import BootstrapSecrets


def test_validate_api_key_accepts_matching_secret() -> None:
    runtime = SimpleNamespace(bootstrap_secrets=BootstrapSecrets(api_key="secret"), settings=SimpleNamespace(auth_mode="api_key"))
    assert validate_api_key("secret", runtime) is True
    assert validate_api_key("wrong", runtime) is False


def test_auth_status_is_redacted() -> None:
    runtime = SimpleNamespace(bootstrap_secrets=BootstrapSecrets(api_key="secret"), settings=SimpleNamespace(auth_mode="api_key"))
    status = auth_status_from_runtime(runtime)
    assert status.api_key_configured is True
    assert status.access_token_present is False
    assert status.refresh_token_present is False
