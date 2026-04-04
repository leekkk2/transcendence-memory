import pytest

from transcendence_memory.bootstrap.models import Topology
from transcendence_memory.handoff.sanitize import endpoint_is_local_only, ensure_exportable_endpoint


def test_same_machine_allows_localhost() -> None:
    assert ensure_exportable_endpoint("http://127.0.0.1:8711", Topology.SAME_MACHINE) == "http://127.0.0.1:8711"


def test_local_only_hosts_are_detected() -> None:
    assert endpoint_is_local_only("http://localhost:8711")
    assert endpoint_is_local_only("http://backend:8711")


def test_split_machine_rejects_localhost() -> None:
    with pytest.raises(ValueError):
        ensure_exportable_endpoint("http://127.0.0.1:8711", Topology.SPLIT_MACHINE)


def test_split_machine_rejects_private_and_reserved_ips() -> None:
    with pytest.raises(ValueError):
        ensure_exportable_endpoint("http://192.168.1.10:8711", Topology.SPLIT_MACHINE)
    with pytest.raises(ValueError):
        ensure_exportable_endpoint("http://198.18.0.1:8711", Topology.SPLIT_MACHINE)


def test_split_machine_allows_public_endpoint() -> None:
    assert ensure_exportable_endpoint("https://memory.example.com", Topology.SPLIT_MACHINE) == "https://memory.example.com"
