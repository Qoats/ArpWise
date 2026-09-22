from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from .network import detect_local_network, parse_network
from .scanner import Device, scan_network


class NetScanPyApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("NetScanPy")
        self.geometry("820x520")
        self.minsize(700, 420)

        self.network_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.count_var = tk.StringVar(value="0 devices")

        self._build_ui()
        self._load_default_network()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top = ttk.Frame(self, padding=(16, 16, 16, 8))
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Network").grid(
            row=0, column=0, padx=(0, 8), sticky="w"
        )

        self.network_entry = ttk.Entry(
            top,
            textvariable=self.network_var,
        )
        self.network_entry.grid(row=0, column=1, sticky="ew")

        self.scan_button = ttk.Button(
            top,
            text="Scan",
            command=self.start_scan,
        )
        self.scan_button.grid(row=0, column=2, padx=(8, 0))

        table_frame = ttk.Frame(self, padding=(16, 8))
        table_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            table_frame,
            columns=("ip", "mac", "hostname"),
            show="headings",
            selectmode="browse",
        )

        self.tree.heading("ip", text="IP address")
        self.tree.heading("mac", text="MAC address")
        self.tree.heading("hostname", text="Hostname")

        self.tree.column("ip", width=150, minwidth=120, anchor="w")
        self.tree.column("mac", width=190, minwidth=160, anchor="w")
        self.tree.column("hostname", width=360, minwidth=180, anchor="w")

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.tree.yview,
        )
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        bottom = ttk.Frame(self, padding=(16, 8, 16, 16))
        bottom.grid(row=2, column=0, sticky="ew")
        bottom.columnconfigure(1, weight=1)

        self.progress = ttk.Progressbar(
            bottom,
            mode="indeterminate",
            length=140,
        )
        self.progress.grid(row=0, column=0, padx=(0, 12))

        ttk.Label(
            bottom,
            textvariable=self.status_var,
        ).grid(row=0, column=1, sticky="w")

        ttk.Label(
            bottom,
            textvariable=self.count_var,
        ).grid(row=0, column=2, sticky="e")

    def _load_default_network(self) -> None:
        try:
            self.network_var.set(str(detect_local_network()))
        except RuntimeError as exc:
            self.network_var.set("")
            self.status_var.set(str(exc))

    def start_scan(self) -> None:
        if self.scan_button.instate(["disabled"]):
            return

        raw_network = self.network_var.get().strip()

        try:
            network = parse_network(raw_network)
        except ValueError as exc:
            messagebox.showerror("NetScanPy", str(exc))
            return

        self._clear_results()
        self.status_var.set(f"Scanning {network}...")
        self.count_var.set("0 devices")
        self.scan_button.state(["disabled"])
        self.network_entry.state(["disabled"])
        self.progress.start(10)

        worker = threading.Thread(
            target=self._scan_worker,
            args=(str(network),),
            daemon=True,
        )
        worker.start()

    def _scan_worker(self, network: str) -> None:
        try:
            devices = scan_network(network)
        except Exception as exc:
            self.after(0, self._scan_failed, str(exc))
            return

        self.after(0, self._scan_finished, devices)

    def _scan_finished(self, devices: list[Device]) -> None:
        for device in devices:
            self.tree.insert(
                "",
                "end",
                values=(device.ip, device.mac, device.hostname),
            )

        count = len(devices)
        self.count_var.set(
            f"{count} device" if count == 1 else f"{count} devices"
        )
        self.status_var.set("Scan complete")
        self._set_idle_state()

    def _scan_failed(self, error: str) -> None:
        self.status_var.set("Scan failed")
        self._set_idle_state()
        messagebox.showerror("NetScanPy", error)

    def _set_idle_state(self) -> None:
        self.progress.stop()
        self.scan_button.state(["!disabled"])
        self.network_entry.state(["!disabled"])
        self.network_entry.focus_set()

    def _clear_results(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)


def main() -> None:
    app = NetScanPyApp()
    app.mainloop()


if __name__ == "__main__":
    main()
