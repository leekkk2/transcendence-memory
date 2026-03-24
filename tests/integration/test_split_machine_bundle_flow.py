from transcendence_memory.backend.settings import load_runtime_config
from transcendence_memory.bootstrap.models import BootstrapConfig, BootstrapSecrets, Role, Topology, TransportHint
from transcendence_memory.bootstrap.paths import resolve_paths
from transcendence_memory.bootstrap.persistence import write_config, write_secrets
from transcendence_memory.handoff.export import build_connection_bundle
from transcendence_memory.handoff.importer import import_connection_bundle


def test_split_machine_bundle_export_import_roundtrip(bootstrap_roots) -> None:
    backend_paths = resolve_paths(
        config_path=bootstrap_roots["config_root"] / "backend",
        secret_path=bootstrap_roots["secret_root"] / "backend",
    )
    write_config(
        BootstrapConfig(
            role=Role.BACKEND,
            topology=Topology.SPLIT_MACHINE,
            transport_hint=TransportHint.DOMAIN_PROXY,
            auth_mode="api_key",
            provider="openai",
            model="text-embedding-3-small",
            base_url="https://api.openai.com/v1",
            advertised_url="https://memory.example.com",
            config_path=str(backend_paths.config_root),
            secret_path=str(backend_paths.secret_root),
        ),
        backend_paths,
    )
    write_secrets(BootstrapSecrets(api_key="backend-secret"), backend_paths)
    runtime = load_runtime_config(
        config_path=backend_paths.config_root,
        secret_path=backend_paths.secret_root,
    )
    bundle = build_connection_bundle(runtime, Topology.SPLIT_MACHINE)

    frontend_paths = resolve_paths(
        config_path=bootstrap_roots["config_root"] / "frontend",
        secret_path=bootstrap_roots["secret_root"] / "frontend",
    )
    imported = import_connection_bundle(frontend_paths, bundle)
    assert imported.advertised_url == "https://memory.example.com"
    assert imported.required_local_inputs == ["api_key"]
