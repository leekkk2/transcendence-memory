from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


SCHEMA_VERSION = 1


class Role(str, Enum):
    BACKEND = "backend"
    FRONTEND = "frontend"
    BOTH = "both"


class Topology(str, Enum):
    SAME_MACHINE = "same_machine"
    SPLIT_MACHINE = "split_machine"


class TransportHint(str, Enum):
    IP_PORT = "ip_port"
    DOMAIN_PROXY = "domain_proxy"


class BootstrapMode(str, Enum):
    INTERACTIVE = "interactive"
    AUTO_RECOMMENDED = "auto_recommended"


class ProviderSettings(BaseModel):
    provider: str = "openai"
    model: str = "text-embedding-3-small"
    base_url: str | None = None


class BootstrapSelection(BaseModel):
    role: Role
    topology: Topology
    transport_hint: TransportHint = TransportHint.IP_PORT
    mode: BootstrapMode = BootstrapMode.AUTO_RECOMMENDED
    provider: ProviderSettings = Field(default_factory=ProviderSettings)
    recommendation_reason: str = "Defaulted to the safest local bootstrap path."


class DetectionResult(BaseModel):
    os_name: str
    shell: str
    docker_available: bool
    docker_compose_available: bool
    config_path_writable: bool
    secret_path_writable: bool
    port_conflicts: list[int] = Field(default_factory=list)
    recommended_role: Role = Role.BOTH
    recommended_topology: Topology = Topology.SAME_MACHINE
    recommendation_reason: str = "Use both + same_machine for the fastest first bootstrap."
    local_ip: str = "127.0.0.1"
    warnings: list[str] = Field(default_factory=list)


class BootstrapConfig(BaseModel):
    schema_version: int = SCHEMA_VERSION
    role: Role
    topology: Topology
    transport_hint: TransportHint
    provider: str
    model: str
    base_url: str | None = None
    config_path: str
    secret_path: str
    deferred_items: list[str] = Field(default_factory=list)


class BootstrapSecrets(BaseModel):
    schema_version: int = SCHEMA_VERSION
    api_key: str | None = None


class BootstrapState(BaseModel):
    schema_version: int = SCHEMA_VERSION
    role: Role
    topology: Topology
    transport_hint: TransportHint
    recommendation_reason: str
    last_plan_summary: dict[str, Any] = Field(default_factory=dict)
    last_config: dict[str, Any] = Field(default_factory=dict)


class ResolvedPaths(BaseModel):
    config_root: Path
    secret_root: Path
    config_file: Path
    secret_file: Path
    state_file: Path


class BootstrapPlan(BaseModel):
    selection: BootstrapSelection
    detection: DetectionResult
    files_to_create: list[str] = Field(default_factory=list)
    files_to_update: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    deferred_items: list[str] = Field(default_factory=list)
    verification_commands: list[str] = Field(default_factory=list)
    diff_summary: list[str] = Field(default_factory=list)
    dry_run: bool = True
