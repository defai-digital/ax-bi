# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""SSRF-aware validation for Admin-configured LLM base URLs."""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Iterable, Sequence
from urllib.parse import urlparse

from axbi.genai.llm_errors import LLMSsrfBlockedError
from axbi.utils.network import is_safe_host

# Always blocked even when private-network LLM gateways are allowed (cloud metadata).
_ALWAYS_BLOCKED_NETWORKS = (
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("0.0.0.0/8"),
)


def _host_matches_allowlist(host: str, allowlist: Sequence[str]) -> bool:
    """Return True when allowlist is empty or host matches a suffix/exact entry."""
    if not allowlist:
        return True
    host_l = host.lower().rstrip(".")
    for entry in allowlist:
        item = entry.strip().lower().rstrip(".")
        if not item:
            continue
        if item.startswith("."):
            suffix = item
            bare = item[1:]
            if host_l == bare or host_l.endswith(suffix):
                return True
        elif host_l == item or host_l.endswith("." + item):
            return True
    return False


def _resolved_ips(host: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        results = socket.getaddrinfo(host, None)
    except socket.gaierror as ex:
        raise LLMSsrfBlockedError(
            f"LLM base URL host cannot be resolved: {host}"
        ) from ex
    ips: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for _, _, _, _, sockaddr in results:
        try:
            ip = ipaddress.ip_address(sockaddr[0])
        except ValueError as ex:
            raise LLMSsrfBlockedError(
                f"LLM base URL resolved to an invalid address: {sockaddr[0]}"
            ) from ex
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        ips.append(ip)
    if not ips:
        raise LLMSsrfBlockedError(f"LLM base URL host resolved to no addresses: {host}")
    return ips


def _any_always_blocked(
    ips: Iterable[ipaddress.IPv4Address | ipaddress.IPv6Address],
) -> bool:
    for ip in ips:
        for net in _ALWAYS_BLOCKED_NETWORKS:
            if ip in net:
                return True
    return False


def validate_llm_base_url(
    base_url: str,
    *,
    allow_http: bool = False,
    allow_private_network: bool = False,
    host_allowlist: Sequence[str] | None = None,
) -> str:
    """Validate an LLM inference base URL and return the normalized URL string.

    :param base_url: Admin-configured base URL (e.g. OpenAI-compatible root).
    :param allow_http: When False, only ``https`` is permitted.
    :param allow_private_network: When True, RFC1918/loopback hosts are allowed
        (on-prem Ollama/LM Studio gateways). Cloud metadata ranges stay blocked.
    :param host_allowlist: Optional host suffixes; empty means no extra filter.
    :returns: Stripped base URL without trailing slash.
    :raises LLMSsrfBlockedError: when the URL fails egress policy.
    """
    if not base_url or not str(base_url).strip():
        raise LLMSsrfBlockedError("LLM base URL is required")

    raw = str(base_url).strip()
    parsed = urlparse(raw)
    scheme = (parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        raise LLMSsrfBlockedError(
            f"LLM base URL scheme must be http or https, got {scheme!r}"
        )
    if scheme == "http" and not allow_http:
        raise LLMSsrfBlockedError(
            "HTTP LLM base URLs are disabled; set allow_http or use HTTPS"
        )
    if not parsed.hostname:
        raise LLMSsrfBlockedError("LLM base URL must include a hostname")
    if parsed.username or parsed.password:
        raise LLMSsrfBlockedError(
            "LLM base URL must not embed credentials; use api_key instead"
        )

    host = parsed.hostname
    allowlist = list(host_allowlist or ())
    if not _host_matches_allowlist(host, allowlist):
        raise LLMSsrfBlockedError(
            f"LLM base URL host {host!r} is not on the configured allowlist"
        )

    ips = _resolved_ips(host)
    if _any_always_blocked(ips):
        raise LLMSsrfBlockedError(
            f"LLM base URL host {host!r} resolves to a blocked network range"
        )

    if not allow_private_network and not is_safe_host(host):
        raise LLMSsrfBlockedError(
            f"LLM base URL host {host!r} is not a public address; "
            "enable GENAI_LLM_ALLOW_PRIVATE_NETWORK for on-prem gateways"
        )

    return raw.rstrip("/")
