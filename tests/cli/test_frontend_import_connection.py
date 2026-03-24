import json

from transcendence_memory.cli import app
from transcendence_memory.handoff.models import BundleAuth, BundleBackend, BundleCompatibility, BundleProvider, ConnectionBundle
from transcendence_memory.bootstrap.models import Topology


def _bundle_json() -> str:
    bundle = ConnectionBundle(
        topology=Topology.SPLIT_MACHINE,
        backend=BundleBackend(advertised_url="https://memory.example.com"),
        auth=BundleAuth(mode="api_key", required_local_inputs=["api_key"]),
        provider=BundleProvider(provider="openai", model="text-embedding-3-small", base_url="https://api.openai.com/v1"),
        compatibility=BundleCompatibility(backend_version="0.1.0"),
    )
    return bundle.model_dump_json()


def test_frontend_import_connection_writes_non_secret_config(bootstrap_roots, runner) -> None:
    result = runner.invoke(
        app,
        [
            "frontend",
            "import-connection",
            "--bundle-json",
            _bundle_json(),
            "--config-path",
            str(bootstrap_roots["config_root"]),
            "--secret-path",
            str(bootstrap_roots["secret_root"]),
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["advertised_url"] == "https://memory.example.com"
    assert "access_token" not in result.stdout
    assert "refresh_token" not in result.stdout
    assert "super-secret" not in result.stdout
