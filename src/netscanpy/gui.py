from __future__ import annotations

import locale
import platform
import subprocess
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

        self.context_menu = tk.Menu(self, tearoff=False)
        self.context_menu.add_command(label="Ping", command=self.ping_selected)
        self.tree.bind("<ButtonRelease-3>", self._show_context_menu)
        self.tree.bind("<Shift-F10>", self._show_context_menu_keyboard)

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

    def _show_context_menu(self, event: tk.Event) -> str:
        item = self.tree.identify_row(event.y)
        if not item:
            return "break"

        self.tree.selection_set(item)
        self.tree.focus(item)
        self.context_menu.post(event.x_root, event.y_root)
        return "break"

    def _show_context_menu_keyboard(self, event: tk.Event) -> str:
        selected = self.tree.selection()
        if not selected:
            children = self.tree.get_children()
            if not children:
                return "break"
            item = children[0]
            self.tree.selection_set(item)
            self.tree.focus(item)
        else:
            item = selected[0]

        x, y, width, height = self.tree.bbox(item)
        root_x = self.tree.winfo_rootx() + x + min(width // 2, 80)
        root_y = self.tree.winfo_rooty() + y + height
        self.context_menu.post(root_x, root_y)
        return "break"

    def ping_selected(self) -> None:
        selected = self.tree.selection()
        if not selected:
            return

        values = self.tree.item(selected[0], "values")
        if not values:
            return

        ip = str(values[0])
        self.status_var.set(f"Pinging {ip}...")

        ping_window = self._create_ping_window(ip)

        worker = threading.Thread(
            target=self._ping_worker,
            args=(ip, ping_window),
            daemon=True,
        )
        worker.start()

    def _windows_oem_encoding(self) -> str:
        try:
            import ctypes

            code_page = ctypes.windll.kernel32.GetOEMCP()
            return f"cp{code_page}"
        except Exception:
            return locale.getpreferredencoding(False) or "utf-8"

    def _ping_worker(self, ip: str, ping_window: dict[str, object]) -> None:
        system = platform.system()

        if system == "Windows":
            command = ["ping", "-n", "4", "-w", "1000", ip]
            encoding = self._windows_oem_encoding()
            creationflags = subprocess.CREATE_NO_WINDOW
        else:
            command = ["ping", "-c", "4", "-W", "1", ip]
            encoding = locale.getpreferredencoding(False) or "utf-8"
            creationflags = 0

        output_parts: list[str] = []

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                creationflags=creationflags,
            )

            if process.stdout is None:
                raise RuntimeError("Unable to read ping output.")

            while True:
                raw_line = process.stdout.readline()
                if not raw_line:
                    break

                line = raw_line.decode(encoding, errors="replace")
                output_parts.append(line)
                self.after(
                    0,
                    self._append_ping_output,
                    ping_window,
                    line,
                )

            return_code = process.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
            self.after(
                0,
                self._ping_failed_window,
                ip,
                ping_window,
                str(exc),
            )
            return

        output = "".join(output_parts).strip()
        self.after(
            0,
            self._ping_finished,
            ip,
            ping_window,
            return_code == 0,
            output,
        )

    def _extract_ping_summary(self, output: str) -> list[str]:
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        selected: list[str] = []

        keywords = (
            "Réponse de",
            "Reply from",
            "Paquets",
            "Packets:",
            "Minimum",
            "Maximum",
            "Moyenne",
            "Average",
            "TTL=",
            "temps=",
            "time=",
        )

        for line in lines:
            if any(keyword in line for keyword in keywords):
                selected.append(line)

        return selected[-8:]

    def _create_ping_window(self, ip: str) -> dict[str, object]:
        window = tk.Toplevel(self)
        window.title(f"Ping {ip}")
        window.geometry("760x500")
        window.minsize(620, 360)
        window.transient(self)

        container = ttk.Frame(window, padding=12)
        container.pack(fill="both", expand=True)

        title_label = ttk.Label(
            container,
            text=f"Ping {ip} - in progress...",
            font=("Segoe UI", 11, "bold"),
        )
        title_label.pack(anchor="w")

        summary_frame = ttk.LabelFrame(
            container,
            text="Summary",
            padding=10,
        )
        summary_frame.pack(fill="x", pady=(10, 10))

        summary_label = ttk.Label(
            summary_frame,
            text="Waiting for ping results...",
            justify="left",
        )
        summary_label.pack(anchor="w")

        terminal_frame = ttk.LabelFrame(
            container,
            text="Terminal output",
            padding=8,
        )
        terminal_frame.pack(fill="both", expand=True)

        text_widget = tk.Text(
            terminal_frame,
            wrap="word",
            font=("Consolas", 10),
            bg="#111111",
            fg="#f0f0f0",
            insertbackground="#f0f0f0",
            relief="flat",
        )
        text_widget.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(
            terminal_frame,
            orient="vertical",
            command=text_widget.yview,
        )
        scrollbar.pack(side="right", fill="y")
        text_widget.configure(yscrollcommand=scrollbar.set)
        text_widget.configure(state="disabled")

        button_frame = ttk.Frame(container)
        button_frame.pack(fill="x", pady=(10, 0))

        def copy_output() -> None:
            text_widget.configure(state="normal")
            output = text_widget.get("1.0", "end-1c")
            text_widget.configure(state="disabled")
            window.clipboard_clear()
            window.clipboard_append(output)

        ttk.Button(
            button_frame,
            text="Copy",
            command=copy_output,
        ).pack(side="left")

        ttk.Button(
            button_frame,
            text="Close",
            command=window.destroy,
        ).pack(side="right")

        window.focus_set()

        return {
            "window": window,
            "title_label": title_label,
            "summary_label": summary_label,
            "text_widget": text_widget,
        }

    def _append_ping_output(
        self,
        ping_window: dict[str, object],
        text: str,
    ) -> None:
        window = ping_window["window"]
        if not isinstance(window, tk.Toplevel) or not window.winfo_exists():
            return

        text_widget = ping_window["text_widget"]
        if not isinstance(text_widget, tk.Text):
            return

        text_widget.configure(state="normal")
        text_widget.insert("end", text)
        text_widget.see("end")
        text_widget.configure(state="disabled")

        summary_label = ping_window.get("summary_label")
        if isinstance(summary_label, ttk.Label):
            current_output = text_widget.get("1.0", "end-1c")
            summary = self._extract_ping_summary(current_output)
            if summary:
                summary_label.configure(text="\n".join(summary[-4:]))

    def _ping_finished(
        self,
        ip: str,
        ping_window: dict[str, object],
        success: bool,
        output: str,
    ) -> None:
        window = ping_window["window"]
        if not isinstance(window, tk.Toplevel) or not window.winfo_exists():
            return

        title_label = ping_window["title_label"]
        summary_label = ping_window["summary_label"]

        if success:
            self.status_var.set(f"{ip} responded to ping")
            if isinstance(title_label, ttk.Label):
                title_label.configure(text=f"Ping {ip} - success")
        else:
            self.status_var.set(f"{ip} did not respond to ping")
            if isinstance(title_label, ttk.Label):
                title_label.configure(text=f"Ping {ip} - no response")

        summary = self._extract_ping_summary(output)
        if isinstance(summary_label, ttk.Label):
            summary_label.configure(
                text=(
                    "\n".join(summary)
                    if summary
                    else "No summary information was returned."
                )
            )

    def _ping_failed_window(
        self,
        ip: str,
        ping_window: dict[str, object],
        error: str,
    ) -> None:
        self.status_var.set(f"Ping failed for {ip}")

        window = ping_window["window"]
        if not isinstance(window, tk.Toplevel) or not window.winfo_exists():
            return

        title_label = ping_window["title_label"]
        summary_label = ping_window["summary_label"]

        if isinstance(title_label, ttk.Label):
            title_label.configure(text=f"Ping {ip} - error")
        if isinstance(summary_label, ttk.Label):
            summary_label.configure(text=error)

        self._append_ping_output(
            ping_window,
            f"\nError: {error}\n",
        )

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
            devices = scan_network(network, timeout=1.0)
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
