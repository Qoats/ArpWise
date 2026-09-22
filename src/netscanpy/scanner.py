from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import ipaddress
import platform
import socket
import struct
import time
from typing import Callable


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


def _sort_devices(devices: list[Device]) -> list[Device]:
    return sorted(
        devices,
        key=lambda device: tuple(int(part) for part in device.ip.split(".")),
    )


def _scan_windows(network: ipaddress.IPv4Network, timeout: float) -> list[Device]:
    """Discover local devices using the native Windows SendARP API."""
    import ctypes
    from ctypes import wintypes

    iphlpapi = ctypes.WinDLL("iphlpapi.dll")
    send_arp = iphlpapi.SendARP
    send_arp.argtypes = [
        wintypes.ULONG,
        wintypes.ULONG,
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.ULONG),
    ]
    send_arp.restype = wintypes.DWORD

    def probe(ip: ipaddress.IPv4Address) -> Device | None:
        destination = struct.unpack("=I", socket.inet_aton(str(ip)))[0]
        mac_buffer = (ctypes.c_ubyte * 8)()
        mac_length = wintypes.ULONG(8)

        result = send_arp(
            destination,
            0,
            ctypes.byref(mac_buffer),
            ctypes.byref(mac_length),
        )

        if result != 0 or mac_length.value == 0:
            return None

        mac = ":".join(
            f"{mac_buffer[index]:02x}" for index in range(mac_length.value)
        )
        return Device(str(ip), mac, resolve_hostname(str(ip)))

    hosts = list(network.hosts())
    # SendARP is blocking. A bounded pool keeps /24 scans reasonably fast.
    workers = min(64, max(1, len(hosts)))
    devices: list[Device] = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(probe, ip): ip for ip in hosts}
        for future in as_completed(futures, timeout=max(timeout * len(hosts), 5.0)):
            try:
                device = future.result()
            except OSError:
                continue
            if device is not None:
                devices.append(device)

    return _sort_devices(devices)


def _read_linux_arp_table(
    network: ipaddress.IPv4Network,
) -> dict[str, str]:
    """Read complete ARP entries belonging to the requested network."""
    devices: dict[str, str] = {}

    try:
        with open("/proc/net/arp", "r", encoding="utf-8") as arp_file:
            next(arp_file, None)
            for line in arp_file:
                columns = line.split()
                if len(columns) < 6:
                    continue

                ip_text, _, flags, mac, _, _ = columns[:6]

                try:
                    ip = ipaddress.ip_address(ip_text)
                except ValueError:
                    continue

                # 0x2 means the ARP entry is complete.
                if (
                    isinstance(ip, ipaddress.IPv4Address)
                    and ip in network
                    and flags == "0x2"
                    and mac != "00:00:00:00:00:00"
                ):
                    devices[ip_text] = mac.lower()
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Linux ARP table /proc/net/arp is not available on this system."
        ) from exc

    return devices


def _scan_linux(network: ipaddress.IPv4Network, timeout: float) -> list[Device]:
    """Discover local devices without Scapy or raw sockets.

    Sending UDP datagrams makes the Linux kernel resolve neighbors with ARP.
    We then read the resulting entries from /proc/net/arp.
    """
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setblocking(False)

    try:
        for ip in network.hosts():
            try:
                # The destination port does not need to be open. On a local
                # subnet, the kernel still performs ARP before transmitting.
                udp_socket.sendto(b"\x00", (str(ip), 9))
            except (BlockingIOError, OSError):
                continue
    finally:
        udp_socket.close()

    # Give the kernel time to complete neighbor resolution.
    time.sleep(timeout)

    entries = _read_linux_arp_table(network)
    devices = [
        Device(ip=ip, mac=mac, hostname=resolve_hostname(ip))
        for ip, mac in entries.items()
    ]
    return _sort_devices(devices)


def scan_network(network: str, timeout: float = 1.5) -> list[Device]:
    """Discover devices on a private local IPv4 network using native OS APIs."""
    parsed = ipaddress.ip_network(network, strict=False)

    if not isinstance(parsed, ipaddress.IPv4Network):
        raise ValueError("Only IPv4 networks are supported.")

    system = platform.system()

    scanners: dict[str, Callable[[ipaddress.IPv4Network, float], list[Device]]] = {
        "Windows": _scan_windows,
        "Linux": _scan_linux,
    }

    scanner = scanners.get(system)
    if scanner is None:
        raise RuntimeError(
            f"Unsupported operating system: {system}. "
            "NetScanPy currently supports Windows and Linux."
        )

    return scanner(parsed, timeout)
