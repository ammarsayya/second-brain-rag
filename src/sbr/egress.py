"""Network egress policy for model providers (T-P7-01, ADR-039/ADR-040).

The owner's decisions Q-B03 and Q-B04 (2026-11-04) allow model calls only to services on this host. This module holds
the pure predicates both the configuration and the gateway use:

* :func:`local_url_problem` validates a provider ``base_url`` at configuration time: ``http``/``https`` only, no
  credentials in the URL, and the host must be a loopback IP literal or exactly ``localhost``.
* :func:`resolves_only_to_loopback` re-checks at call time that the host resolves to loopback addresses only.

What this does **not** do: it is not a network sandbox. It controls the addresses sbr's own adapters connect to. A
process-level or OS-level egress block (firewall, sandbox profile) remains a deployment responsibility (docs/22 §8).
It has no sbr imports so :mod:`sbr.config` can use it without an import cycle.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit

LOCALHOST_NAMES = frozenset({"localhost"})


def is_loopback_host(host: str) -> bool:
    """True for ``localhost`` and loopback IP literals (``127.0.0.0/8``, ``::1``). Never resolves names."""
    name = host.strip().lower().rstrip(".")
    if name in LOCALHOST_NAMES:
        return True
    try:
        return ipaddress.ip_address(name.strip("[]")).is_loopback
    except ValueError:
        return False


def local_url_problem(url: str) -> str | None:
    """Return why ``url`` is not an acceptable local model endpoint, or ``None`` if it is."""
    try:
        parts = urlsplit(url)
        port = parts.port  # raises ValueError for a malformed port
    except ValueError as exc:
        return f"malformed URL ({exc})"
    if parts.scheme not in {"http", "https"}:
        return f"scheme must be http or https, got {parts.scheme or '<none>'!r}"
    if parts.username is not None or parts.password is not None:
        return "credentials must not be embedded in the URL (use api_key_env)"
    host = parts.hostname
    if not host:
        return "URL has no host"
    if not is_loopback_host(host):
        return (
            f"host {host!r} is not a loopback address; remote model providers are disabled "
            "(owner decisions Q-B03/Q-B04, ADR-039/ADR-040)"
        )
    if parts.query or parts.fragment:
        return "base URL must not carry a query or fragment"
    del port
    return None


def resolves_only_to_loopback(host: str, port: int) -> bool:
    """True if every address ``host`` resolves to is loopback. IP literals are checked without DNS."""
    if not is_loopback_host(host):
        return False
    name = host.strip().strip("[]")
    try:
        ipaddress.ip_address(name)
    except ValueError:
        pass
    else:
        return True
    try:
        infos = socket.getaddrinfo(name, port, type=socket.SOCK_STREAM)
    except OSError:
        return False
    addresses = {str(info[4][0]) for info in infos}
    return bool(addresses) and all(ipaddress.ip_address(a.split("%")[0]).is_loopback for a in addresses)
