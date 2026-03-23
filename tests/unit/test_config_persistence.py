from transcendence_memory.bootstrap.detect import detect_environment
from transcendence_memory.bootstrap.models import BootstrapSecrets, BootstrapSelection, ProviderSettings, Role, Topology, TransportHint
from transcendence_memory.bootstrap.paths import resolve_paths
from transcendence_memory.bootstrap.persistence import build_bootstrap_config, read_config, write_config, write_secrets


def test_config_and_secret_files_are_separate(bootstrap_roots) -> None:
    paths = resolve_paths(
        config_path=bootstrap_roots["config_root"],
        secret_path=bootstrap_roots["secret_root"],
    )
    detection = detect_environment(paths, requested_role=Role.BOTH)
    selection = BootstrapSelection(
        role=Role.BOTH,
        topology=Topology.SAME_MACHINE,
        transport_hint=TransportHint.IP_PORT,
        provider=ProviderSettings(provider="openai", model="text-embedding-3-small"),
    )
    config = build_bootstrap_config(selection, paths, detection)
    write_config(config, paths)
    write_secrets(BootstrapSecrets(api_key="secret-token"), paths)

    loaded = read_config(paths)
    assert loaded is not None
    assert loaded.provider == "openai"
    assert "secret-token" not in paths.config_file.read_text(encoding="utf-8")
    assert "secret-token" in paths.secret_file.read_text(encoding="utf-8")
