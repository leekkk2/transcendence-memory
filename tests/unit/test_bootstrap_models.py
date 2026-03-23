from transcendence_memory.bootstrap.models import Role, Topology, TransportHint


def test_role_values_are_stable() -> None:
    assert Role.BACKEND.value == "backend"
    assert Role.FRONTEND.value == "frontend"
    assert Role.BOTH.value == "both"


def test_topology_values_are_stable() -> None:
    assert Topology.SAME_MACHINE.value == "same_machine"
    assert Topology.SPLIT_MACHINE.value == "split_machine"


def test_transport_hint_values_are_stable() -> None:
    assert TransportHint.IP_PORT.value == "ip_port"
    assert TransportHint.DOMAIN_PROXY.value == "domain_proxy"
