from __future__ import annotations

from dataclasses import dataclass
import socket

from scapy.all import ARP, Ether, srp  # type: ignore[import-untyped]


@dataclass(slots=True)
class Device:
    ip: str
    mac: str
    hostname: str


def resolve_hostname(ip: str) -> str:
    """Resolve a hostname without failing the whole scan."""
    try:
        return socket.gethostbyaddr(ip)[0]
    except (socket.herror, socket.gaierror, TimeoutError, OSError):
        return "Unknown"


def scan_network(network: str, timeout: float = 1.5) -> list[Device]:
    """Discover devices on a local IPv4 network using ARP."""
    packet = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=network)
    answered, _ = srp(packet, timeout=timeout, verbose=False)

    devices: dict[str, Device] = {}

    for _, response in answered:
        ip = str(response.psrc)
        mac = str(response.hwsrc).lower()
        devices[ip] = Device(
            ip=ip,
            mac=mac,
            hostname=resolve_hostname(ip),
        )

    def ip_key(device: Device) -> tuple[int, ...]:
        return tuple(int(part) for part in device.ip.split("."))

    return sorted(devices.values(), key=ip_key)
