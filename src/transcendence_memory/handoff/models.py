from __future__ import annotations

from datetime import datetime, UTC

from pydantic import BaseModel, Field, model_validator

from transcendence_memory.bootstrap.models import Topology


BUNDLE_VERSION = "1"


def default_frontend_handoff_steps(mode: str) -> list[str]:
    if mode == "oauth":
        return [
            "前端机器先执行 transcendence-memory frontend import-connection --bundle-file <bundle.json>",
            "然后执行 transcendence-memory auth login ... 完成本地 OAuth 登录",
            "再执行 transcendence-memory frontend check",
            "最后执行 transcendence-memory frontend smoke",
        ]
    if mode == "api_key":
        return [
            "前端机器先执行 transcendence-memory frontend import-connection --bundle-file <bundle.json>",
            "然后执行 transcendence-memory auth set-api-key --api-key <frontend-local-api-key>",
            "再执行 transcendence-memory frontend check",
            "最后执行 transcendence-memory frontend smoke",
        ]
    return [
        "前端机器先执行 transcendence-memory frontend import-connection --bundle-file <bundle.json>",
        "然后补齐本地 auth material",
        "再执行 transcendence-memory frontend check 与 transcendence-memory frontend smoke",
    ]


class BundleBackend(BaseModel):
    advertised_url: str
    health_path: str = "/api/v1/health"
    embed_path: str = "/api/v1/memory/embed"
    search_path: str = "/api/v1/memory/search"


class BundleAuth(BaseModel):
    mode: str
    required_local_inputs: list[str] = Field(default_factory=list)
    frontend_handoff_steps: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def apply_default_handoff_steps(self) -> "BundleAuth":
        if not self.frontend_handoff_steps:
            self.frontend_handoff_steps = default_frontend_handoff_steps(self.mode)
        return self


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
