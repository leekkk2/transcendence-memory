from __future__ import annotations

from pathlib import Path

from transcendence_memory.__init__ import __version__
from transcendence_memory.backend.settings import LoadedRuntimeConfig
from transcendence_memory.bootstrap.models import Topology
from transcendence_memory.handoff.models import (
    BUNDLE_VERSION,
    BundleAuth,
    BundleBackend,
    BundleCompatibility,
    BundleProvider,
    ConnectionBundle,
)
from transcendence_memory.handoff.sanitize import ensure_exportable_endpoint


def required_local_inputs(auth_mode: str) -> list[str]:
    if auth_mode == "oauth":
        return ["oauth_login"]
    if auth_mode == "api_key":
        return ["api_key"]
    return ["local_auth_material"]


def build_connection_bundle(runtime: LoadedRuntimeConfig, topology: Topology) -> ConnectionBundle:
    advertised_url = ensure_exportable_endpoint(runtime.settings.advertised_url, topology)
    return ConnectionBundle(
        topology=topology,
        backend=BundleBackend(
            advertised_url=advertised_url,
            health_path=runtime.settings.health_path,
            embed_path=runtime.settings.embed_path,
            search_path=runtime.settings.search_path,
        ),
        auth=BundleAuth(
            mode=runtime.settings.auth_mode,
            required_local_inputs=required_local_inputs(runtime.settings.auth_mode),
        ),
        provider=BundleProvider(
            provider=runtime.settings.provider,
            model=runtime.settings.model,
            base_url=runtime.settings.provider_base_url,
        ),
        compatibility=BundleCompatibility(
            backend_version=__version__,
            bundle_version=BUNDLE_VERSION,
        ),
    )


def dump_bundle(bundle: ConnectionBundle, output: Path | None = None) -> str:
    rendered = bundle.model_dump_json(indent=2)
    if output is not None:
        output.write_text(rendered, encoding="utf-8")
    return rendered
