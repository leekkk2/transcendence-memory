from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

from transcendence_memory.bootstrap.models import Topology


LOCAL_ONLY_HOSTS = {
    "127.0.0.1",
    "localhost",
    "0.0.0.0",
    "::1",
    "backend",
    "postgres",
    "db",
    "host.docker.internal",
}


def _hostname_is_non_public_ip(hostname: str) -> bool:
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return not address.is_global


def endpoint_is_local_only(url: str) -> bool:
    hostname = urlparse(url).hostname or ""
    if hostname in LOCAL_ONLY_HOSTS:
        return True
    if _hostname_is_non_public_ip(hostname):
        return True
    if "." not in hostname and hostname not in {"", None}:
        return True
    return False


def ensure_exportable_endpoint(url: str, topology: Topology) -> str:
    if topology == Topology.SAME_MACHINE:
        return url
    if endpoint_is_local_only(url):
        raise ValueError("Split-machine export requires a public or advertised endpoint, not a local-only address.")
    return url
