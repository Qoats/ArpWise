from __future__ import annotations

import argparse
import sys

from rich.console import Console

from .display import show_devices
from .network import detect_local_network, parse_network
from .scanner import scan_network


console = Console(stderr=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="netscanpy",
        description="Discover devices on a local IPv4 network.",
    )
    parser.add_argument(
        "-n",
        "--network",
        help="Private IPv4 CIDR to scan, for example 192.168.1.0/24.",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=float,
        default=1.5,
        help="ARP response timeout in seconds (default: 1.5).",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.timeout <= 0:
        console.print("[red]Error:[/red] timeout must be greater than zero.")
        raise SystemExit(2)

    try:
        network = (
            parse_network(args.network)
            if args.network
            else detect_local_network()
        )
        devices = scan_network(str(network), timeout=args.timeout)
    except PermissionError:
        console.print(
            "[red]Permission denied.[/red] Run NetScanPy with administrator/root privileges."
        )
        raise SystemExit(1)
    except (RuntimeError, ValueError, OSError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(1)

    show_devices(devices, str(network))


if __name__ == "__main__":
    main()
