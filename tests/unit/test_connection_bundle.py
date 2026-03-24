from transcendence_memory.handoff.models import BundleAuth, BundleBackend, BundleCompatibility, BundleProvider, ConnectionBundle
from transcendence_memory.bootstrap.models import Topology


def test_connection_bundle_has_expected_fields() -> None:
    bundle = ConnectionBundle(
        topology=Topology.SPLIT_MACHINE,
        backend=BundleBackend(advertised_url="https://memory.example"),
        auth=BundleAuth(mode="api_key", required_local_inputs=["api_key"]),
        provider=BundleProvider(provider="openai", model="text-embedding-3-small", base_url="https://api.openai.com/v1"),
        compatibility=BundleCompatibility(backend_version="0.1.0"),
    )
    payload = bundle.model_dump()
    assert payload["bundle_version"] == "1"
    assert payload["backend"]["advertised_url"] == "https://memory.example"
    assert payload["auth"]["required_local_inputs"] == ["api_key"]


def test_connection_bundle_serialization_has_no_secret_fields() -> None:
    bundle = ConnectionBundle(
        topology=Topology.SAME_MACHINE,
        backend=BundleBackend(advertised_url="http://127.0.0.1:8000"),
        auth=BundleAuth(mode="oauth", required_local_inputs=["oauth_login"]),
        provider=BundleProvider(provider="openai", model="text-embedding-3-small"),
        compatibility=BundleCompatibility(backend_version="0.1.0"),
    )
    serialized = bundle.model_dump_json()
    assert "api_key" not in serialized
    assert "access_token" not in serialized
    assert "refresh_token" not in serialized
