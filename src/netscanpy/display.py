from __future__ import annotations

from rich.console import Console
from rich.table import Table

from .scanner import Device


console = Console()


def show_devices(devices: list[Device], network: str) -> None:
    console.print(f"\n[bold]NetScanPy[/bold]")
    console.print(f"Network: [cyan]{network}[/cyan]\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("IP address")
    table.add_column("MAC address")
    table.add_column("Hostname")

    for device in devices:
        table.add_row(device.ip, device.mac, device.hostname)

    console.print(table)

    count = len(devices)
    console.print(f"\n[bold green]{count}[/bold green] device{'s' if count != 1 else ''} found.")
