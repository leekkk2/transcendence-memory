from transcendence_memory.bootstrap.models import BootstrapSecrets
from transcendence_memory.bootstrap.paths import resolve_paths
from transcendence_memory.bootstrap.persistence import write_secrets
from transcendence_memory.cli import app
from transcendence_memory.handoff.models import BundleAuth, BundleBackend, BundleCompatibility, BundleProvider, ConnectionBundle
from transcendence_memory.bootstrap.models import Topology


def test_same_machine_import_then_smoke(monkeypatch, bootstrap_roots, runner) -> None:
    bundle = ConnectionBundle(
        topology=Topology.SAME_MACHINE,
        backend=BundleBackend(advertised_url="http://127.0.0.1:8000"),
        auth=BundleAuth(mode="api_key", required_local_inputs=["api_key"]),
        provider=BundleProvider(provider="openai", model="text-embedding-3-small", base_url="https://api.openai.com/v1"),
        compatibility=BundleCompatibility(backend_version="0.1.0"),
    )
    imported = runner.invoke(
        app,
        [
            "frontend",
            "import-connection",
            "--bundle-json",
            bundle.model_dump_json(),
            "--config-path",
            str(bootstrap_roots["config_root"]),
            "--secret-path",
            str(bootstrap_roots["secret_root"]),
        ],
    )
    assert imported.exit_code == 0

    paths = resolve_paths(
        config_path=bootstrap_roots["config_root"],
        secret_path=bootstrap_roots["secret_root"],
    )
    write_secrets(BootstrapSecrets(api_key="secret"), paths)
    monkeypatch.setattr(
        "transcendence_memory.cli.run_smoke_checks",
        lambda runtime: {"health": {"status": "ok"}, "embed": {"id": "r1"}, "search": {"count": 1}},
    )
    smoke = runner.invoke(
        app,
        [
            "frontend",
            "smoke",
            "--config-path",
            str(bootstrap_roots["config_root"]),
            "--secret-path",
            str(bootstrap_roots["secret_root"]),
        ],
    )
    assert smoke.exit_code == 0
    assert '"count": 1' in smoke.stdout
