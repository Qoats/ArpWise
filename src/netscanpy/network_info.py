from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import json
import socket
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import psutil


@dataclass(slots=True)
class LocalNetworkInfo:
    interface: str
    ip: str
    netmask: str
    network: str
    prefix_length: int


@dataclass(slots=True)
class PublicNetworkInfo:
    ip: str = "—"
    city: str = "—"
    region: str = "—"
    country: str = "—"
    country_code: str = "—"
    postal: str = "—"
    latitude: str = "—"
    longitude: str = "—"
    timezone: str = "—"
    utc_offset: str = "—"
    asn: str = "—"
    organization: str = "—"
    currency: str = "—"
    languages: str = "—"


def get_local_network_info() -> LocalNetworkInfo | None:
    """Return the most relevant private IPv4 interface on the host."""
    candidates: list[tuple[int, LocalNetworkInfo]] = []

    for interface, addresses in psutil.net_if_addrs().items():
        for address in addresses:
            if address.family != socket.AF_INET or not address.address or not address.netmask:
                continue

            try:
                ip = ipaddress.ip_address(address.address)
                network = ipaddress.ip_network(
                    f"{address.address}/{address.netmask}", strict=False
                )
            except ValueError:
                continue

            if (
                not isinstance(ip, ipaddress.IPv4Address)
                or ip.is_loopback
                or ip.is_link_local
                or not ip.is_private
            ):
                continue

            info = LocalNetworkInfo(
                interface=interface,
                ip=str(ip),
                netmask=address.netmask,
                network=str(network),
                prefix_length=network.prefixlen,
            )
            candidates.append((abs(network.prefixlen - 24), info))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def fetch_public_network_info(timeout: float = 5.0) -> PublicNetworkInfo:
    """Fetch public IP geolocation and ASN information over HTTPS.

    IP geolocation is approximate and applies to the public Internet address,
    not to individual devices using private LAN addresses.
    """
    request = Request(
        "https://ipapi.co/json/",
        headers={
            "Accept": "application/json",
            "User-Agent": "NetScanPy/0.3 (+https://github.com/evergreen-stack/NetScanPy)",
        },
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Unable to retrieve public network information: {exc}") from exc

    if payload.get("error"):
        reason = payload.get("reason") or "unknown API error"
        raise RuntimeError(f"Unable to retrieve public network information: {reason}")

    def text(key: str) -> str:
        value = payload.get(key)
        if value is None or value == "":
            return "—"
        return str(value)

    return PublicNetworkInfo(
        ip=text("ip"),
        city=text("city"),
        region=text("region"),
        country=text("country_name"),
        country_code=text("country_code"),
        postal=text("postal"),
        latitude=text("latitude"),
        longitude=text("longitude"),
        timezone=text("timezone"),
        utc_offset=text("utc_offset"),
        asn=text("asn"),
        organization=text("org"),
        currency=text("currency"),
        languages=text("languages"),
    )
