from __future__ import annotations

from tkinter import messagebox

from .gui_modern import ModernNetScanPyApp
from .network import detect_local_network


class AutoDetectNetScanPyApp(ModernNetScanPyApp):
    """Modern GUI that always scans the currently active local network."""

    def __init__(self) -> None:
        super().__init__()
        # Let the window finish rendering first, then discover and scan the LAN.
        self.after(450, self._auto_scan_on_startup)

    def _detect_active_network(self, show_error: bool = True) -> str | None:
        try:
            network = str(detect_local_network())
        except RuntimeError as exc:
            self.network_var.set("")
            self.network_stat_var.set("—")
            self.status_var.set(str(exc))
            if show_error:
                messagebox.showerror("NetScanPy", str(exc))
            return None

        self.network_var.set(network)
        self.network_stat_var.set(network)
        return network

    def _auto_scan_on_startup(self) -> None:
        if self._detect_active_network(show_error=False) is not None:
            super().start_scan()

    def start_scan(self) -> None:
        # Re-detect every time so changing Wi-Fi/Ethernet/VPN does not leave
        # NetScanPy scanning an old subnet.
        if self.scan_button.instate(["disabled"]):
            return
        if self._detect_active_network(show_error=True) is None:
            return
        super().start_scan()


def main() -> None:
    app = AutoDetectNetScanPyApp()
    app.mainloop()


if __name__ == "__main__":
    main()
