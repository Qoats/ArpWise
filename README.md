# NetScanPy

NetScanPy is a lightweight open-source tool, written in Rust, for discovering devices on your local network.

No Npcap. No raw sockets. NetScanPy uses native operating-system features:

- **Windows**: the built-in `SendARP` API from `iphlpapi.dll`
- **Linux**: normal UDP sockets to trigger neighbour discovery, then `/proc/net/arp`

Two programs are built from the same code: `netscanpy` (terminal) and `netscanpy-gui` (graphical interface, egui).

> Use NetScanPy only on networks you own or are authorized to inspect.

## Features

- IPv4 device discovery (IP, MAC, hostname), automatic local network detection
- Manufacturer lookup from the IEEE registry (downloaded once, not bundled)
- Latency of every device, measured in parallel
- Device history: first/last seen, new devices flagged, known devices that went offline
- Export to CSV or JSON
- Custom TCP port scan (`22,80,8000-8100`), ping, traceroute
- Wake-on-LAN
- Device labels, search and column sorting in the GUI
- Single executable, no runtime to install

## Build

Requires a recent stable [Rust](https://rustup.rs) toolchain (and the MSVC build tools on Windows).

```bash
cargo build --release
```

The binaries are in `target/release/`.

## Command line

```bash
netscanpy                                  # scan the detected local network
netscanpy --network 192.168.1.0/24         # scan a specific private network
netscanpy --ping --output devices.csv      # add latency, export (.csv or .json)
netscanpy --update-vendors                 # download the manufacturer database
netscanpy ports 192.168.1.10 --range 22,80,8000-8100
netscanpy wake aa:bb:cc:dd:ee:ff
```

Devices are remembered between scans: new ones are flagged `NEW`, and known devices that do not answer are listed. Use `--no-history` to disable this.

## GUI

Run `netscanpy-gui`. The network is detected automatically; click **Scanner** to scan, select a device to see its details and actions, and use **Exporter…** or **Fabricants** in the top bar.

## Where data is stored

`%APPDATA%\NetScanPy` on Windows, `~/.config/NetScanPy` on Linux: `devices.json` (labels), `history.json` and `oui.csv` (manufacturers).

## Current limitations

NetScanPy focuses on devices reachable on the same local IPv4 subnet. ARP does not cross routers, so devices on other routed networks are outside the scope of this discovery method. Private networks of /16 or smaller only.

## License

GNU General Public License v3.0. See `LICENSE`.
