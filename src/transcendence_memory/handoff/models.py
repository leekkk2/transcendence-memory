from __future__ import annotations

from datetime import datetime, UTC

from pydantic import BaseModel, Field

from transcendence_memory.bootstrap.models import Topology


BUNDLE_VERSION = "1"


class BundleBackend(BaseModel):
    advertised_url: str
    health_path: str = "/api/v1/health"
    embed_path: str = "/api/v1/memory/embed"
    search_path: str = "/api/v1/memory/search"


class BundleAuth(BaseModel):
    mode: str
    required_local_inputs: list[str] = Field(default_factory=list)


class BundleProvider(BaseModel):
    provider: str
    model: str
    base_url: str | None = None


class BundleCompatibility(BaseModel):
    backend_version: str
    bundle_version: str = BUNDLE_VERSION


class ConnectionBundle(BaseModel):
    bundle_version: str = BUNDLE_VERSION
    generated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    topology: Topology
    backend: BundleBackend
    auth: BundleAuth
    provider: BundleProvider
    compatibility: BundleCompatibility
