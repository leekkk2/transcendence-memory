import json

from transcendence_memory.backend.settings import load_runtime_config
from transcendence_memory.bootstrap.models import BootstrapConfig, BootstrapSecrets, Role, Topology, TransportHint
from transcendence_memory.bootstrap.paths import resolve_paths
from transcendence_memory.bootstrap.persistence import write_config, write_secrets
from transcendence_memory.cli import app


def _write_backend_config(bootstrap_roots, *, advertised_url: str, auth_mode: str = "api_key") -> None:
    paths = resolve_paths(
        config_path=bootstrap_roots["config_root"],
        secret_path=bootstrap_roots["secret_root"],
    )
    write_config(
        BootstrapConfig(
            role=Role.BACKEND,
            topology=Topology.SPLIT_MACHINE,
            transport_hint=TransportHint.IP_PORT,
            auth_mode=auth_mode,
            provider="openai",
            model="text-embedding-3-small",
            base_url="https://api.openai.com/v1",
            advertised_url=advertised_url,
            config_path=str(paths.config_root),
            secret_path=str(paths.secret_root),
        ),
        paths,
    )
    write_secrets(BootstrapSecrets(api_key="super-secret"), paths)


def test_backend_export_connection_is_redacted(bootstrap_roots, runner) -> None:
    _write_backend_config(bootstrap_roots, advertised_url="https://memory.example.com")
    result = runner.invoke(
        app,
        [
            "backend",
            "export-connection",
            "--topology",
            "split_machine",
            "--config-path",
            str(bootstrap_roots["config_root"]),
            "--secret-path",
            str(bootstrap_roots["secret_root"]),
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["bundle_version"] == "1"
    assert payload["backend"]["advertised_url"] == "https://memory.example.com"
    assert "super-secret" not in result.stdout
    assert payload["auth"]["required_local_inputs"] == ["api_key"]


def test_backend_export_connection_rejects_local_split_machine_endpoint(bootstrap_roots, runner) -> None:
    _write_backend_config(bootstrap_roots, advertised_url="http://127.0.0.1:8000")
    result = runner.invoke(
        app,
        [
            "backend",
            "export-connection",
            "--topology",
            "split_machine",
            "--config-path",
            str(bootstrap_roots["config_root"]),
            "--secret-path",
            str(bootstrap_roots["secret_root"]),
        ],
    )
    assert result.exit_code == 1
    assert "public or advertised backend URL" in result.stdout
