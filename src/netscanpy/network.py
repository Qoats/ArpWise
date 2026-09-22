from __future__ import annotations

import ipaddress
import socket

import psutil


def detect_local_network() -> ipaddress.IPv4Network:
    """Return the first usable private IPv4 network found on the host."""
    candidates: list[ipaddress.IPv4Network] = []

    for addresses in psutil.net_if_addrs().values():
        for addr in addresses:
            if addr.family != socket.AF_INET or not addr.address or not addr.netmask:
                continue

            ip = ipaddress.ip_address(addr.address)
            if ip.is_loopback or ip.is_link_local:
                continue

            try:
                network = ipaddress.ip_network(
                    f"{addr.address}/{addr.netmask}",
                    strict=False,
                )
            except ValueError:
                continue

            if ip.is_private:
                candidates.append(network)

    if not candidates:
        raise RuntimeError("No usable private IPv4 network was detected.")

    # Prefer typical LAN-sized subnets over extremely broad virtual networks.
    candidates.sort(key=lambda net: abs(net.prefixlen - 24))
    return candidates[0]


def parse_network(value: str) -> ipaddress.IPv4Network:
    """Parse and validate a private IPv4 network supplied by the user."""
    try:
        network = ipaddress.ip_network(value, strict=False)
    except ValueError as exc:
        raise ValueError(f"Invalid network: {value}") from exc

    if not isinstance(network, ipaddress.IPv4Network):
        raise ValueError("Only IPv4 networks are supported.")

    if not network.is_private:
        raise ValueError("NetScanPy only scans private IPv4 networks.")

    return network
