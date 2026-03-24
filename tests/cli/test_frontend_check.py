from transcendence_memory.bootstrap.models import BootstrapSecrets, Topology
from transcendence_memory.bootstrap.paths import resolve_paths
from transcendence_memory.bootstrap.persistence import write_secrets
from transcendence_memory.cli import app
from transcendence_memory.handoff.models import BundleAuth, BundleBackend, BundleCompatibility, BundleProvider, ConnectionBundle


def _bundle_json() -> str:
    bundle = ConnectionBundle(
        topology=Topology.SPLIT_MACHINE,
        backend=BundleBackend(advertised_url="https://memory.example.com"),
        auth=BundleAuth(mode="api_key", required_local_inputs=["api_key"]),
        provider=BundleProvider(provider="openai", model="text-embedding-3-small", base_url="https://api.openai.com/v1"),
        compatibility=BundleCompatibility(backend_version="0.1.0"),
    )
    return bundle.model_dump_json()


def test_frontend_check_reports_missing_local_auth_state(bootstrap_roots, runner) -> None:
    import_result = runner.invoke(
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
    assert import_result.exit_code == 0

    result = runner.invoke(
        app,
        [
            "frontend",
            "check",
            "--config-path",
            str(bootstrap_roots["config_root"]),
            "--secret-path",
            str(bootstrap_roots["secret_root"]),
        ],
    )
    assert result.exit_code == 1
    assert "missing_local_inputs" in result.stdout
    assert "api_key" in result.stdout


def test_frontend_check_passes_with_local_api_key(monkeypatch, bootstrap_roots, runner) -> None:
    import_result = runner.invoke(
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
    assert import_result.exit_code == 0
    paths = resolve_paths(
        config_path=bootstrap_roots["config_root"],
        secret_path=bootstrap_roots["secret_root"],
    )
    write_secrets(BootstrapSecrets(api_key="secret"), paths)
    monkeypatch.setattr("transcendence_memory.cli.probe_backend_service", lambda runtime: (True, {"status": "ok"}, None))

    result = runner.invoke(
        app,
        [
            "frontend",
            "check",
            "--config-path",
            str(bootstrap_roots["config_root"]),
            "--secret-path",
            str(bootstrap_roots["secret_root"]),
        ],
    )
    assert result.exit_code == 0
    assert '"service_reachable": true' in result.stdout.lower()
