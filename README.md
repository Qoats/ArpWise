# NetScanPy

NetScanPy is a lightweight open-source Python tool for discovering devices on your local network.

**No Npcap. No Scapy.** NetScanPy uses native operating-system networking features:

- **Windows:** the built-in `SendARP` API from `iphlpapi.dll`
- **Linux:** normal UDP sockets to trigger neighbor discovery, then `/proc/net/arp`

It displays:

- IPv4 address
- MAC address
- Hostname when available
- Automatic local network detection
- Clean terminal output with Rich
- Optional manual CIDR selection

> Use NetScanPy only on networks you own or are authorized to inspect.

## Requirements

- Python 3.11+
- Windows 10/11 or Linux
- No Npcap required
- No Scapy required
- No root/admin privileges normally required

## Installation

Clone the repository:

```bash
git clone https://github.com/evergreen-stack/NetScanPy.git
cd NetScanPy
```

Create a virtual environment:

```bash
python -m venv .venv
```

### Windows PowerShell

You do not have to activate the virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\netscanpy.exe
```

If PowerShell allows virtual-environment activation, you can alternatively use:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e .
netscanpy
```

### Linux

```bash
source .venv/bin/activate
pip install -e .
netscanpy
```

## Usage

Scan the automatically detected local network:

```bash
netscanpy
```

Scan a specific private network:

```bash
netscanpy --network 192.168.1.0/24
```

Change the neighbor-discovery wait time:

```bash
netscanpy --timeout 2
```

## How it works

### Windows

NetScanPy calls the Windows `SendARP` API directly with Python's standard-library `ctypes` module. This allows it to obtain the MAC address associated with local IPv4 devices without installing a packet-capture driver.

### Linux

NetScanPy sends a tiny UDP datagram to each address in the selected local subnet. The Linux kernel performs ARP neighbor resolution before attempting delivery. NetScanPy then reads completed entries from `/proc/net/arp`.

The target UDP port does not need to be open.

## Example

```text
NetScanPy
Network: 192.168.1.0/24

┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ IP address    ┃ MAC address       ┃ Hostname         ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ 192.168.1.1   │ aa:bb:cc:dd:ee:ff │ router           │
│ 192.168.1.42  │ 11:22:33:44:55:66 │ desktop          │
└───────────────┴───────────────────┴──────────────────┘

2 devices found.
```

## Current limitations

NetScanPy v0.2 focuses on devices reachable on the same local IPv4 subnet. ARP does not cross routers, so devices on other routed networks are outside the scope of this discovery method.

## Roadmap

- MAC vendor identification
- JSON and CSV export
- Device history
- Detection of new devices
- Optional port discovery
- Graphical interface

## License

GNU General Public License v3.0. See [LICENSE](LICENSE).
