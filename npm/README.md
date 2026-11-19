# ArpWise

A fast, driver-free network scanner for Windows and Linux. It lists every device on the local network, with its manufacturer and latency, and flags new ones.

```bash
npm install -g arpwise

arpwise                       # scan the local network in the terminal
arpwise --ping --output devices.csv
arpwise-gui                   # open the graphical app
```

The npm package downloads the matching program for the system (Windows or Linux, x64, 32-bit or ARM64) from the [GitHub release](https://github.com/Qoats/ArpWise/releases) and checks its SHA-256 before installing it.

- Website and direct downloads: https://qoats.github.io/ArpWise/
- Source code: https://github.com/Qoats/ArpWise
- Contact: support@axim.ch

Use ArpWise only on networks you own or are authorized to inspect. Licensed under GPL-3.0.
