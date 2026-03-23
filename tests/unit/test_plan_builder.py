from transcendence_memory.bootstrap.detect import detect_environment
from transcendence_memory.bootstrap.models import BootstrapSelection, ProviderSettings, Role, Topology, TransportHint
from transcendence_memory.bootstrap.paths import resolve_paths
from transcendence_memory.bootstrap.persistence import build_bootstrap_config
from transcendence_memory.bootstrap.planner import build_bootstrap_plan, render_plan


def test_split_machine_without_domain_falls_back_to_ip_port(bootstrap_roots) -> None:
    paths = resolve_paths(
        config_path=bootstrap_roots["config_root"],
        secret_path=bootstrap_roots["secret_root"],
    )
    detection = detect_environment(paths, requested_role=Role.BACKEND)
    selection = BootstrapSelection(
        role=Role.BACKEND,
        topology=Topology.SPLIT_MACHINE,
        transport_hint=TransportHint.IP_PORT,
        provider=ProviderSettings(provider="openai", model="text-embedding-3-small"),
        recommendation_reason="Test recommendation",
    )
    config = build_bootstrap_config(selection, paths, detection)
    plan = build_bootstrap_plan(
        selection=selection,
        detection=detection,
        paths=paths,
        desired_config=config,
        current_config=None,
        dry_run=True,
    )

    rendered = render_plan(plan)
    assert "ip_port" in rendered
    assert "Deferred Items" in rendered
    assert any("Split-machine bootstrap is using IP + port" in item for item in plan.deferred_items)
