# ArpWise

**See everything on your network, in one click.** ArpWise is a fast, driver-free network scanner for Windows and Linux. It finds every device on your local network, tells you who made it, how fast it answers, and warns you when something new shows up.

Written in Rust. One small executable. No Npcap, no Wireshark, no admin tools to install.

> Use ArpWise only on networks you own or are authorized to inspect.

## Why ArpWise

- **Nothing to install first.** It uses what your system already has: the native `SendARP` API on Windows, kernel neighbour discovery and `/proc/net/arp` on Linux.
- **Know who is on your network.** Every device with its IP, MAC address, hostname and manufacturer.
- **Spot intruders.** ArpWise remembers what it has seen, flags new devices, and keeps known ones that went offline.
- **Fast.** A full /24 scan takes seconds, and latency is measured for every device in parallel.
- **Two ways to use it.** A clean graphical app (dark or light) and a scriptable command line.

## Features

- IPv4 discovery with automatic local network detection
- Manufacturer lookup from the IEEE registry (downloaded once, never bundled)
- Latency of every device, with a colour indicator
- Device history: first and last seen, new devices flagged, offline devices kept
- Automatic rescans (30 s to 15 min)
- Search, filters (new, slow, no ping reply), sortable columns, custom labels
- Right-click actions: ping, traceroute, port scan, open in browser, Wake-on-LAN, copy IP or MAC
- Custom TCP port scan (`22,80,8000-8100`)
- Export to CSV or JSON
- Public IP and approximate location

## Install

Requires a recent stable [Rust](https://rustup.rs) toolchain (and the MSVC build tools on Windows).

```bash
cargo build --release
```

You get two programs in `target/release/`:

| Program | What it is |
|---|---|
| `arpwise-gui` | The graphical app |
| `arpwise` | The command line |

## Command line

```bash
arpwise                                  # scan the detected local network
arpwise --network 192.168.1.0/24         # scan a specific private network
arpwise --ping --output devices.csv      # add latency, export (.csv or .json)
arpwise --update-vendors                 # download the manufacturer database
arpwise ports 192.168.1.10 --range 22,80,8000-8100
arpwise wake aa:bb:cc:dd:ee:ff
```

Devices are remembered between scans: new ones are flagged `NEW`, and known devices that do not answer are listed. Use `--no-history` to turn this off.

## Graphical app

Run `arpwise-gui`. The network is detected automatically. Click **Scanner**, select a device to see its details, or right-click it for quick actions. Use **Exporter…** to save the list and **Fabricants** to download the manufacturer database. Theme, automatic rescans and offline devices are in the **Réglages** tab.

## Where your data lives

`%APPDATA%\ArpWise` on Windows, `~/.config/ArpWise` on Linux: labels (`devices.json`), history (`history.json`), settings (`settings.json`) and manufacturers (`oui.csv`). Data from the earlier name, NetScanPy, is moved there automatically.

## Limits

ArpWise finds devices on the same local IPv4 subnet. ARP does not cross routers, so devices on other routed networks are out of reach. Only private networks of /16 or smaller are scanned.

## License

GNU General Public License v3.0. See `LICENSE`.
