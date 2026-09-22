# NetScanPy

NetScanPy is a lightweight open-source Python tool for discovering devices on your local network.

**No Npcap. No Scapy.** NetScanPy uses native operating-system networking features:

- **Windows:** the built-in `SendARP` API from `iphlpapi.dll`
- **Linux:** normal UDP sockets to trigger neighbor discovery, then `/proc/net/arp`

NetScanPy can be used from the terminal or through a Tkinter graphical interface.

## Features

- IPv4 address discovery
- MAC address discovery
- Hostname resolution when available
- Automatic local network detection
- Terminal interface
- Graphical interface
- Manual CIDR selection
- No Npcap
- No Scapy

> Use NetScanPy only on networks you own or are authorized to inspect.

## Requirements

- Python 3.11+
- Windows 10/11 or Linux
- No Npcap required
- No Scapy required

On Linux, Tkinter may need to be installed separately by your distribution if you want to use the GUI.

For Debian/Ubuntu:

```bash
sudo apt install python3-tk
```

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

You do not need to activate the virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

Launch the graphical interface:

```powershell
.\.venv\Scripts\netscanpy-gui.exe
```

Launch the terminal interface:

```powershell
.\.venv\Scripts\netscanpy.exe
```

### Linux

```bash
source .venv/bin/activate
pip install -e .
```

Graphical interface:

```bash
netscanpy-gui
```

Terminal interface:

```bash
netscanpy
```

## CLI usage

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

## GUI

The graphical interface automatically detects the local network.

Enter or change a CIDR such as:

```text
192.168.1.0/24
```

Then click **Scan**.

The scan runs in a background thread so the window remains responsive.

The results table shows:

- IP address
- MAC address
- Hostname

## How it works

### Windows

NetScanPy calls the Windows `SendARP` API directly with Python's standard-library `ctypes` module. This allows it to obtain the MAC address associated with local IPv4 devices without installing a packet-capture driver.

### Linux

NetScanPy sends a tiny UDP datagram to each address in the selected local subnet. The Linux kernel performs ARP neighbor resolution before attempting delivery. NetScanPy then reads completed entries from `/proc/net/arp`.

The target UDP port does not need to be open.

## Current limitations

NetScanPy focuses on devices reachable on the same local IPv4 subnet. ARP does not cross routers, so devices on other routed networks are outside the scope of this discovery method.

## Roadmap

- MAC vendor identification
- JSON and CSV export
- Device history
- Detection of new devices
- Optional port discovery
- GUI improvements

## License

GNU General Public License v3.0. See [LICENSE](LICENSE).
