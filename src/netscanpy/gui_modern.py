from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .gui import NetScanPyApp, TRANSLATIONS


EXTRA_TRANSLATIONS = {
    "fr": {
        "selected_device": "Détails de l'appareil",
        "quick_actions": "Actions",
        "search_label": "Rechercher",
        "inventory": "Inventaire réseau",
        "devices_online": "Appareils",
    },
    "en": {
        "selected_device": "Device details",
        "quick_actions": "Actions",
        "search_label": "Search",
        "inventory": "Network inventory",
        "devices_online": "Devices",
    },
    "de": {
        "selected_device": "Gerätedetails",
        "quick_actions": "Aktionen",
        "search_label": "Suchen",
        "inventory": "Netzwerkinventar",
        "devices_online": "Geräte",
    },
    "zh": {
        "selected_device": "设备详情",
        "quick_actions": "操作",
        "search_label": "搜索",
        "inventory": "网络资产",
        "devices_online": "设备",
    },
}

for language, values in EXTRA_TRANSLATIONS.items():
    TRANSLATIONS.setdefault(language, {}).update(values)


class ModernNetScanPyApp(NetScanPyApp):
    """Professional dark-only network console."""

    def __init__(self) -> None:
        self.theme = "dark"
        super().__init__()
        self.theme = "dark"
        self.title("NetScanPy")
        self.geometry("1280x780")
        self.minsize(1020, 640)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        # Product bar.
        self.header = ttk.Frame(self, style="Header.TFrame", padding=(24, 0))
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.columnconfigure(0, weight=1)
        self.header.configure(height=58)
        self.header.grid_propagate(False)

        self.brand_title = ttk.Label(self.header, text="NetScanPy", style="Brand.TLabel")
        self.brand_title.grid(row=0, column=0, sticky="w", pady=17)

        self.header_actions = ttk.Frame(self.header, style="Header.TFrame")
        self.header_actions.grid(row=0, column=1, sticky="e")

        # Command bar.
        self.command_bar = ttk.Frame(self, style="Command.TFrame", padding=(24, 14))
        self.command_bar.grid(row=1, column=0, sticky="ew")
        self.command_bar.columnconfigure(1, weight=1)

        self.network_label = ttk.Label(
            self.command_bar, text=self._t("network"), style="CommandLabel.TLabel"
        )
        self.network_label.grid(row=0, column=0, sticky="w", padx=(0, 12))

        self.network_entry = ttk.Entry(
            self.command_bar,
            textvariable=self.network_var,
            style="Modern.TEntry",
            font=("Segoe UI", 10),
        )
        self.network_entry.grid(row=0, column=1, sticky="ew", ipady=5)

        self.scan_button = ttk.Button(
            self.command_bar,
            text=self._t("scan"),
            command=self.start_scan,
            style="Accent.TButton",
        )
        self.scan_button.grid(row=0, column=2, padx=(10, 0), ipadx=14, ipady=3)

        # Compact operational status line instead of decorative statistic cards.
        self.summary_bar = ttk.Frame(self, style="Summary.TFrame", padding=(24, 9))
        self.summary_bar.grid(row=2, column=0, sticky="ew")

        self.summary_devices_title = ttk.Label(
            self.summary_bar, text=self._t("devices_online"), style="SummaryKey.TLabel"
        )
        self.summary_devices_title.pack(side="left")
        self.summary_devices_value = ttk.Label(
            self.summary_bar, textvariable=self.count_var, style="SummaryValue.TLabel"
        )
        self.summary_devices_value.pack(side="left", padx=(7, 22))

        ttk.Separator(self.summary_bar, orient="vertical").pack(side="left", fill="y", padx=(0, 22))

        self.summary_network_title = ttk.Label(
            self.summary_bar, text=self._t("current_network"), style="SummaryKey.TLabel"
        )
        self.summary_network_title.pack(side="left")
        self.summary_network_value = ttk.Label(
            self.summary_bar, textvariable=self.network_stat_var, style="SummaryValue.TLabel"
        )
        self.summary_network_value.pack(side="left", padx=(7, 22))

        ttk.Separator(self.summary_bar, orient="vertical").pack(side="left", fill="y", padx=(0, 22))

        self.summary_status_title = ttk.Label(
            self.summary_bar, text=self._t("status"), style="SummaryKey.TLabel"
        )
        self.summary_status_title.pack(side="left")
        self.summary_status_value = ttk.Label(
            self.summary_bar, textvariable=self.status_var, style="StatusValue.TLabel"
        )
        self.summary_status_value.pack(side="left", padx=(7, 0))

        # Workspace.
        workspace = ttk.Frame(self, style="Root.TFrame", padding=(18, 18, 18, 20))
        workspace.grid(row=3, column=0, sticky="nsew")
        workspace.columnconfigure(0, weight=1)
        workspace.columnconfigure(1, weight=0)
        workspace.rowconfigure(0, weight=1)

        # Main inventory surface.
        self.content_card = ttk.Frame(workspace, style="Panel.TFrame")
        self.content_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.content_card.columnconfigure(0, weight=1)
        self.content_card.rowconfigure(2, weight=1)

        table_header = ttk.Frame(self.content_card, style="Panel.TFrame", padding=(18, 15))
        table_header.grid(row=0, column=0, sticky="ew")
        table_header.columnconfigure(0, weight=1)

        self.devices_title = ttk.Label(
            table_header, text=self._t("inventory"), style="SectionTitle.TLabel"
        )
        self.devices_title.grid(row=0, column=0, sticky="w")

        search_wrap = ttk.Frame(table_header, style="Panel.TFrame")
        search_wrap.grid(row=0, column=1, sticky="e")

        self.search_label = ttk.Label(
            search_wrap, text=self._t("search_label"), style="SearchLabel.TLabel"
        )
        self.search_label.pack(side="left", padx=(0, 8))

        self.search_entry = ttk.Entry(
            search_wrap,
            textvariable=self.search_var,
            style="Search.TEntry",
            width=28,
            font=("Segoe UI", 9),
        )
        self.search_entry.pack(side="left", ipady=3)

        ttk.Separator(self.content_card, orient="horizontal").grid(
            row=1, column=0, sticky="ew"
        )

        table_wrap = ttk.Frame(self.content_card, style="Panel.TFrame")
        table_wrap.grid(row=2, column=0, sticky="nsew")
        table_wrap.columnconfigure(0, weight=1)
        table_wrap.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            table_wrap,
            columns=("ip", "mac", "hostname", "label"),
            show="headings",
            selectmode="browse",
            style="Enterprise.Treeview",
        )
        for column, title in (
            ("ip", self._t("ip")),
            ("mac", self._t("mac")),
            ("hostname", self._t("hostname")),
            ("label", self._t("label")),
        ):
            self.tree.heading(column, text=title)

        self.tree.column("ip", width=150, minwidth=120, anchor="w")
        self.tree.column("mac", width=195, minwidth=160, anchor="w")
        self.tree.column("hostname", width=280, minwidth=180, anchor="w")
        self.tree.column("label", width=180, minwidth=120, anchor="w")

        scrollbar = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.progress = ttk.Progressbar(
            self.content_card,
            mode="indeterminate",
            style="Accent.Horizontal.TProgressbar",
        )
        self.progress.grid(row=3, column=0, sticky="ew")

        # Right-side device inspector.
        self.detail_card = ttk.Frame(workspace, style="Inspector.TFrame")
        self.detail_card.grid(row=0, column=1, sticky="ns")
        self.detail_card.configure(width=312)
        self.detail_card.grid_propagate(False)
        self.detail_card.columnconfigure(0, weight=1)

        inspector_header = ttk.Frame(self.detail_card, style="Inspector.TFrame", padding=(18, 16))
        inspector_header.grid(row=0, column=0, sticky="ew")
        self.detail_title = ttk.Label(
            inspector_header,
            text=self._t("selected_device"),
            style="InspectorTitle.TLabel",
        )
        self.detail_title.pack(anchor="w")

        ttk.Separator(self.detail_card, orient="horizontal").grid(
            row=1, column=0, sticky="ew"
        )

        inspector_body = ttk.Frame(self.detail_card, style="Inspector.TFrame", padding=(18, 16))
        inspector_body.grid(row=2, column=0, sticky="nsew")
        inspector_body.columnconfigure(0, weight=1)

        self.selected_ip_var = tk.StringVar(value="—")
        self.selected_mac_var = tk.StringVar(value="—")
        self.selected_host_var = tk.StringVar(value="—")
        self.selected_label_var = tk.StringVar(value="—")

        self.detail_value_labels: list[ttk.Label] = []
        row = 0
        for key, variable in (
            ("ip", self.selected_ip_var),
            ("mac", self.selected_mac_var),
            ("hostname", self.selected_host_var),
            ("label", self.selected_label_var),
        ):
            key_label = ttk.Label(
                inspector_body,
                text=self._t(key),
                style="InspectorKey.TLabel",
            )
            key_label.grid(row=row, column=0, sticky="w")
            value_label = ttk.Label(
                inspector_body,
                textvariable=variable,
                style="InspectorValue.TLabel",
                wraplength=265,
            )
            value_label.grid(row=row + 1, column=0, sticky="w", pady=(3, 15))
            self.detail_value_labels.append(key_label)
            row += 2

        ttk.Separator(inspector_body, orient="horizontal").grid(
            row=row, column=0, sticky="ew", pady=(2, 15)
        )
        row += 1

        self.quick_actions_label = ttk.Label(
            inspector_body,
            text=self._t("quick_actions"),
            style="InspectorKey.TLabel",
        )
        self.quick_actions_label.grid(row=row, column=0, sticky="w", pady=(0, 8))
        row += 1

        self.quick_buttons: list[ttk.Button] = []
        for text_key, command, style_name in (
            ("ping", self.ping_selected, "PrimaryAction.TButton"),
            ("traceroute", self.traceroute_selected, "Inspector.TButton"),
            ("scan_ports", self.scan_common_ports_selected, "Inspector.TButton"),
            ("open_browser", self.open_in_browser_selected, "Inspector.TButton"),
        ):
            button = ttk.Button(
                inspector_body,
                text=self._t(text_key),
                command=command,
                style=style_name,
            )
            button.grid(row=row, column=0, sticky="ew", pady=3)
            button.state(["disabled"])
            self.quick_buttons.append(button)
            row += 1

        self.context_menu = tk.Menu(self, tearoff=False)
        self._populate_context_menu()
        self.tree.bind("<ButtonRelease-3>", self._show_context_menu)
        self.tree.bind("<Shift-F10>", self._show_context_menu_keyboard)
        self.tree.bind("<Double-1>", lambda _e: self.show_details_selected())
        self.tree.bind("<<TreeviewSelect>>", self._on_device_selected)

    def _build_menus(self) -> None:
        self.language_menu = tk.Menu(self, tearoff=False)
        self.interface_menu = tk.Menu(self, tearoff=False)

        self.language_choice = tk.StringVar(value=self.language)
        for label, value in (
            ("Français", "fr"),
            ("English", "en"),
            ("Deutsch", "de"),
            ("中文", "zh"),
        ):
            self.language_menu.add_radiobutton(
                label=label,
                variable=self.language_choice,
                value=value,
                command=lambda v=value: self._set_language(v),
            )

        self.language_button = ttk.Menubutton(
            self.header_actions,
            text=self._t("language"),
            menu=self.language_menu,
            style="Header.TMenubutton",
        )
        self.language_button.pack(side="left")

    def _set_theme(self, _theme: str) -> None:
        self.theme = "dark"
        self._apply_theme()

    def _on_device_selected(self, _event: object | None = None) -> None:
        values = self._selected_device_values()
        if not values:
            for variable in (
                self.selected_ip_var,
                self.selected_mac_var,
                self.selected_host_var,
                self.selected_label_var,
            ):
                variable.set("—")
            for button in self.quick_buttons:
                button.state(["disabled"])
            return

        ip, mac, hostname, label = values
        self.selected_ip_var.set(ip)
        self.selected_mac_var.set(mac)
        self.selected_host_var.set(hostname or self._t("unknown"))
        self.selected_label_var.set(label or self._t("none"))
        for button in self.quick_buttons:
            button.state(["!disabled"])

    def _refresh_device_table(self) -> None:
        super()._refresh_device_table()
        children = self.tree.get_children()
        if children and not self.tree.selection():
            self.tree.selection_set(children[0])
            self.tree.focus(children[0])
        self._on_device_selected()

    def _apply_language(self) -> None:
        self.network_label.configure(text=self._t("network"))
        self.scan_button.configure(text=self._t("scan"))
        self.language_button.configure(text=self._t("language"))

        self.tree.heading("ip", text=self._t("ip"))
        self.tree.heading("mac", text=self._t("mac"))
        self.tree.heading("hostname", text=self._t("hostname"))
        self.tree.heading("label", text=self._t("label"))
        self._populate_context_menu()

        self.count_var.set(self._t("device_count", count=len(self.devices)))
        if self.status_var.get() in ("Ready", "Prêt", "Bereit", "就绪"):
            self.status_var.set(self._t("ready"))

        self.summary_devices_title.configure(text=self._t("devices_online"))
        self.summary_network_title.configure(text=self._t("current_network"))
        self.summary_status_title.configure(text=self._t("status"))
        self.devices_title.configure(text=self._t("inventory"))
        self.search_label.configure(text=self._t("search_label"))
        self.detail_title.configure(text=self._t("selected_device"))
        self.quick_actions_label.configure(text=self._t("quick_actions"))

        for label, key in zip(
            self.detail_value_labels,
            ("ip", "mac", "hostname", "label"),
        ):
            label.configure(text=self._t(key))

        for button, key in zip(
            self.quick_buttons,
            ("ping", "traceroute", "scan_ports", "open_browser"),
        ):
            button.configure(text=self._t(key))

    def _apply_theme(self) -> None:
        self.theme = "dark"
        super()._apply_theme()
        style = ttk.Style(self)

        root = "#0b0f14"
        header = "#0d1117"
        command = "#11161d"
        panel = "#11161d"
        inspector = "#0f141b"
        field = "#0b1016"
        border = "#28313d"
        border_soft = "#202833"
        fg = "#e7edf5"
        muted = "#8b98a9"
        accent = "#2f81f7"
        accent_hover = "#4b92f8"
        selected = "#173a63"
        hover = "#18212c"
        status = "#7ee2a8"

        self.configure(bg=root)

        style.configure("Root.TFrame", background=root)
        style.configure("Header.TFrame", background=header)
        style.configure("Command.TFrame", background=command)
        style.configure("Summary.TFrame", background="#0e131a")
        style.configure("Panel.TFrame", background=panel)
        style.configure("Inspector.TFrame", background=inspector)

        style.configure(
            "Brand.TLabel",
            background=header,
            foreground=fg,
            font=("Segoe UI Semibold", 16),
        )
        style.configure(
            "Header.TMenubutton",
            background=header,
            foreground=muted,
            bordercolor=border_soft,
            lightcolor=border_soft,
            darkcolor=border_soft,
            padding=(11, 6),
            font=("Segoe UI", 9),
        )
        style.map(
            "Header.TMenubutton",
            background=[("active", hover), ("pressed", hover)],
            foreground=[("active", fg)],
        )

        style.configure(
            "CommandLabel.TLabel",
            background=command,
            foreground=muted,
            font=("Segoe UI Semibold", 9),
        )
        style.configure(
            "Modern.TEntry",
            fieldbackground=field,
            foreground=fg,
            insertcolor=fg,
            bordercolor=border,
            lightcolor=border,
            darkcolor=border,
            padding=(10, 7),
        )
        style.configure(
            "Accent.TButton",
            background=accent,
            foreground="#ffffff",
            bordercolor=accent,
            lightcolor=accent,
            darkcolor=accent,
            padding=(14, 7),
            font=("Segoe UI Semibold", 9),
        )
        style.map(
            "Accent.TButton",
            background=[("active", accent_hover), ("pressed", accent_hover)],
        )

        style.configure(
            "SummaryKey.TLabel",
            background="#0e131a",
            foreground=muted,
            font=("Segoe UI", 8),
        )
        style.configure(
            "SummaryValue.TLabel",
            background="#0e131a",
            foreground=fg,
            font=("Segoe UI Semibold", 8),
        )
        style.configure(
            "StatusValue.TLabel",
            background="#0e131a",
            foreground=status,
            font=("Segoe UI Semibold", 8),
        )

        style.configure(
            "SectionTitle.TLabel",
            background=panel,
            foreground=fg,
            font=("Segoe UI Semibold", 12),
        )
        style.configure(
            "SearchLabel.TLabel",
            background=panel,
            foreground=muted,
            font=("Segoe UI", 8),
        )
        style.configure(
            "Search.TEntry",
            fieldbackground=field,
            foreground=fg,
            insertcolor=fg,
            bordercolor=border,
            lightcolor=border,
            darkcolor=border,
            padding=(9, 6),
        )

        style.configure(
            "Enterprise.Treeview",
            background="#0d131a",
            fieldbackground="#0d131a",
            foreground="#d7dee8",
            borderwidth=0,
            rowheight=36,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Enterprise.Treeview.Heading",
            background="#151c25",
            foreground="#99a6b8",
            bordercolor=border_soft,
            relief="flat",
            padding=(10, 9),
            font=("Segoe UI Semibold", 8),
        )
        style.map(
            "Enterprise.Treeview",
            background=[("selected", selected)],
            foreground=[("selected", "#ffffff")],
        )
        style.map(
            "Enterprise.Treeview.Heading",
            background=[("active", "#1a2330")],
        )

        style.configure(
            "InspectorTitle.TLabel",
            background=inspector,
            foreground=fg,
            font=("Segoe UI Semibold", 11),
        )
        style.configure(
            "InspectorKey.TLabel",
            background=inspector,
            foreground=muted,
            font=("Segoe UI Semibold", 8),
        )
        style.configure(
            "InspectorValue.TLabel",
            background=inspector,
            foreground=fg,
            font=("Segoe UI", 10),
        )
        style.configure(
            "PrimaryAction.TButton",
            background=accent,
            foreground="#ffffff",
            bordercolor=accent,
            padding=(10, 7),
            font=("Segoe UI Semibold", 9),
        )
        style.map(
            "PrimaryAction.TButton",
            background=[("active", accent_hover), ("pressed", accent_hover)],
            foreground=[("disabled", "#697687")],
        )
        style.configure(
            "Inspector.TButton",
            background="#151c25",
            foreground=fg,
            bordercolor=border,
            lightcolor=border,
            darkcolor=border,
            padding=(10, 7),
            font=("Segoe UI", 9),
        )
        style.map(
            "Inspector.TButton",
            background=[("active", hover), ("pressed", hover)],
            foreground=[("disabled", "#697687")],
        )

        style.configure(
            "Accent.Horizontal.TProgressbar",
            troughcolor="#0d131a",
            background=accent,
            bordercolor="#0d131a",
            lightcolor=accent,
            darkcolor=accent,
        )
        style.configure("TSeparator", background=border_soft)

        for menu in (self.language_menu, self.interface_menu, self.context_menu):
            menu.configure(
                background="#151c25",
                foreground=fg,
                activebackground=selected,
                activeforeground="#ffffff",
                selectcolor=accent,
                borderwidth=0,
            )

        self._apply_windows_titlebar_theme()


def main() -> None:
    app = ModernNetScanPyApp()
    app.mainloop()


if __name__ == "__main__":
    main()
