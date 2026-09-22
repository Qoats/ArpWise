# NetScanPy

NetScanPy is a lightweight open-source Python tool for discovering devices on a local network.

It scans a private IPv4 subnet with ARP and displays:

- IPv4 address
- MAC address
- Hostname when available
- Automatic local network detection
- Clean terminal output with Rich
- Optional manual CIDR selection

> Use NetScanPy only on networks you own or are authorized to inspect.

## Requirements

- Python 3.11+
- Windows or Linux
- Administrator/root privileges may be required for ARP scanning

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

Windows:

```powershell
.venv\Scripts\activate
pip install -e .
```

Linux:

```bash
source .venv/bin/activate
pip install -e .
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

Change the ARP timeout:

```bash
netscanpy --timeout 2
```

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

## Roadmap

Planned ideas:

- MAC vendor identification
- JSON and CSV export
- Device history
- Detection of new devices
- Optional port discovery
- Graphical interface

## License

MIT
