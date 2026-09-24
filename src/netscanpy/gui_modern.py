from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .gui import NetScanPyApp, TRANSLATIONS


EXTRA_TRANSLATIONS = {
    "fr": {
        "selected_device": "Appareil sélectionné",
        "select_device_hint": "Sélectionne un appareil pour afficher ses informations et ses actions rapides.",
        "quick_actions": "Actions rapides",
        "discovery": "Découverte réseau",
        "discovery_hint": "Scanne ton réseau local et interagis directement avec les appareils détectés.",
        "search_label": "Recherche",
    },
    "en": {
        "selected_device": "Selected device",
        "select_device_hint": "Select a device to view its information and quick actions.",
        "quick_actions": "Quick actions",
        "discovery": "Network discovery",
        "discovery_hint": "Scan your local network and interact directly with detected devices.",
        "search_label": "Search",
    },
    "de": {
        "selected_device": "Ausgewähltes Gerät",
        "select_device_hint": "Wähle ein Gerät aus, um Informationen und Schnellaktionen anzuzeigen.",
        "quick_actions": "Schnellaktionen",
        "discovery": "Netzwerkerkennung",
        "discovery_hint": "Scanne dein lokales Netzwerk und interagiere direkt mit erkannten Geräten.",
        "search_label": "Suche",
    },
    "zh": {
        "selected_device": "已选设备",
        "select_device_hint": "选择设备后可查看信息并使用快捷操作。",
        "quick_actions": "快捷操作",
        "discovery": "网络发现",
        "discovery_hint": "扫描本地网络并直接操作检测到的设备。",
        "search_label": "搜索",
    },
}

for language, values in EXTRA_TRANSLATIONS.items():
    TRANSLATIONS.setdefault(language, {}).update(values)


class ModernNetScanPyApp(NetScanPyApp):
    def __init__(self) -> None:
        super().__init__()
        self.title("NetScanPy")
        self.geometry("1180x740")
        self.minsize(940, 620)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        # Compact application header.
        self.header = ttk.Frame(self, style="Header.TFrame", padding=(24, 14))
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.columnconfigure(0, weight=1)

        brand = ttk.Frame(self.header, style="Header.TFrame")
        brand.grid(row=0, column=0, sticky="w")
        self.brand_title = ttk.Label(brand, text="NetScanPy", style="Brand.TLabel")
        self.brand_title.pack(anchor="w")
        self.brand_subtitle = ttk.Label(
            brand, text=self._t("app_subtitle"), style="Subtitle.TLabel"
        )
        self.brand_subtitle.pack(anchor="w", pady=(1, 0))

        self.header_actions = ttk.Frame(self.header, style="Header.TFrame")
        self.header_actions.grid(row=0, column=1, sticky="e")

        # Discovery panel.
        self.scan_card = ttk.Frame(self, style="Hero.TFrame", padding=(22, 18))
        self.scan_card.grid(row=1, column=0, sticky="ew", padx=24, pady=(18, 12))
        self.scan_card.columnconfigure(1, weight=1)

        hero_text = ttk.Frame(self.scan_card, style="Hero.TFrame")
        hero_text.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 24))
        self.discovery_title = ttk.Label(
            hero_text, text=self._t("discovery"), style="HeroTitle.TLabel"
        )
        self.discovery_title.pack(anchor="w")
        self.discovery_hint = ttk.Label(
            hero_text,
            text=self._t("discovery_hint"),
            style="HeroSubtitle.TLabel",
            wraplength=320,
        )
        self.discovery_hint.pack(anchor="w", pady=(4, 0))

        self.network_label = ttk.Label(
            self.scan_card, text=self._t("network"), style="HeroField.TLabel"
        )
        self.network_label.grid(row=0, column=1, sticky="w", pady=(0, 6))

        self.network_entry = ttk.Entry(
            self.scan_card,
            textvariable=self.network_var,
            style="Modern.TEntry",
            font=("Segoe UI", 11),
        )
        self.network_entry.grid(row=1, column=1, sticky="ew", ipady=5)

        self.scan_button = ttk.Button(
            self.scan_card,
            text=self._t("scan"),
            command=self.start_scan,
            style="Accent.TButton",
        )
        self.scan_button.grid(row=1, column=2, padx=(12, 0), ipadx=16, ipady=3)

        # Compact statistics.
        self.stats = ttk.Frame(self, style="Root.TFrame")
        self.stats.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 12))
        for i in range(3):
            self.stats.columnconfigure(i, weight=1, uniform="stats")
        self.devices_card = self._make_stat_card(
            self.stats, 0, self._t("devices"), self.count_var
        )
        self.network_card = self._make_stat_card(
            self.stats, 1, self._t("current_network"), self.network_stat_var
        )
        self.status_card = self._make_stat_card(
            self.stats, 2, self._t("status"), self.status_var
        )

        # Workspace: device list + live details panel.
        workspace = ttk.Frame(self, style="Root.TFrame")
        workspace.grid(row=3, column=0, sticky="nsew", padx=24, pady=(0, 20))
        workspace.columnconfigure(0, weight=1)
        workspace.columnconfigure(1, weight=0)
        workspace.rowconfigure(0, weight=1)

        self.content_card = ttk.Frame(workspace, style="Card.TFrame", padding=(18, 16))
        self.content_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.content_card.columnconfigure(0, weight=1)
        self.content_card.rowconfigure(2, weight=1)

        list_header = ttk.Frame(self.content_card, style="Card.TFrame")
        list_header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        list_header.columnconfigure(0, weight=1)
        self.devices_title = ttk.Label(
            list_header, text=self._t("devices"), style="SectionTitle.TLabel"
        )
        self.devices_title.grid(row=0, column=0, sticky="w")

        search_row = ttk.Frame(self.content_card, style="Card.TFrame")
        search_row.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        search_row.columnconfigure(1, weight=1)
        self.search_label = ttk.Label(
            search_row, text=self._t("search_label"), style="FieldLabel.TLabel"
        )
        self.search_label.grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.search_entry = ttk.Entry(
            search_row,
            textvariable=self.search_var,
            style="Search.TEntry",
            font=("Segoe UI", 10),
        )
        self.search_entry.grid(row=0, column=1, sticky="ew", ipady=4)

        table_wrap = ttk.Frame(self.content_card, style="Card.TFrame")
        table_wrap.grid(row=2, column=0, sticky="nsew")
        table_wrap.columnconfigure(0, weight=1)
        table_wrap.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            table_wrap,
            columns=("ip", "mac", "hostname", "label"),
            show="headings",
            selectmode="browse",
            style="Modern.Treeview",
        )
        for column, title in (
            ("ip", self._t("ip")),
            ("mac", self._t("mac")),
            ("hostname", self._t("hostname")),
            ("label", self._t("label")),
        ):
            self.tree.heading(column, text=title)
        self.tree.column("ip", width=135, minwidth=110, anchor="w")
        self.tree.column("mac", width=180, minwidth=150, anchor="w")
        self.tree.column("hostname", width=230, minwidth=150, anchor="w")
        self.tree.column("label", width=150, minwidth=110, anchor="w")

        scrollbar = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.progress = ttk.Progressbar(
            self.content_card,
            mode="indeterminate",
            style="Accent.Horizontal.TProgressbar",
        )
        self.progress.grid(row=3, column=0, sticky="ew", pady=(12, 0))

        # Interactive device inspector.
        self.detail_card = ttk.Frame(workspace, style="Detail.TFrame", padding=(20, 18))
        self.detail_card.grid(row=0, column=1, sticky="ns", ipadx=4)
        self.detail_card.configure(width=300)
        self.detail_card.grid_propagate(False)
        self.detail_card.columnconfigure(0, weight=1)

        self.detail_title = ttk.Label(
            self.detail_card,
            text=self._t("selected_device"),
            style="DetailTitle.TLabel",
        )
        self.detail_title.grid(row=0, column=0, sticky="w")
        self.detail_hint = ttk.Label(
            self.detail_card,
            text=self._t("select_device_hint"),
            style="DetailHint.TLabel",
            wraplength=250,
            justify="left",
        )
        self.detail_hint.grid(row=1, column=0, sticky="ew", pady=(6, 18))

        self.selected_ip_var = tk.StringVar(value="—")
        self.selected_mac_var = tk.StringVar(value="—")
        self.selected_host_var = tk.StringVar(value="—")
        self.selected_label_var = tk.StringVar(value="—")

        self.detail_value_labels: list[ttk.Label] = []
        row = 2
        for key, variable in (
            ("ip", self.selected_ip_var),
            ("mac", self.selected_mac_var),
            ("hostname", self.selected_host_var),
            ("label", self.selected_label_var),
        ):
            label = ttk.Label(
                self.detail_card, text=self._t(key), style="DetailKey.TLabel"
            )
            label.grid(row=row, column=0, sticky="w", pady=(0, 2))
            value = ttk.Label(
                self.detail_card,
                textvariable=variable,
                style="DetailValue.TLabel",
                wraplength=250,
            )
            value.grid(row=row + 1, column=0, sticky="w", pady=(0, 12))
            self.detail_value_labels.append(label)
            row += 2

        self.quick_actions_label = ttk.Label(
            self.detail_card,
            text=self._t("quick_actions"),
            style="DetailKey.TLabel",
        )
        self.quick_actions_label.grid(row=row, column=0, sticky="w", pady=(8, 8))
        row += 1

        self.quick_buttons: list[ttk.Button] = []
        for text_key, command, style_name in (
            ("ping", self.ping_selected, "Accent.TButton"),
            ("traceroute", self.traceroute_selected, "Secondary.TButton"),
            ("scan_ports", self.scan_common_ports_selected, "Secondary.TButton"),
            ("open_browser", self.open_in_browser_selected, "Secondary.TButton"),
        ):
            button = ttk.Button(
                self.detail_card,
                text=self._t(text_key),
                command=command,
                style=style_name,
            )
            button.grid(row=row, column=0, sticky="ew", pady=4)
            button.state(["disabled"])
            self.quick_buttons.append(button)
            row += 1

        self.context_menu = tk.Menu(self, tearoff=False)
        self._populate_context_menu()
        self.tree.bind("<ButtonRelease-3>", self._show_context_menu)
        self.tree.bind("<Shift-F10>", self._show_context_menu_keyboard)
        self.tree.bind("<Double-1>", lambda _e: self.show_details_selected())
        self.tree.bind("<<TreeviewSelect>>", self._on_device_selected)

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
            self.detail_hint.configure(text=self._t("select_device_hint"))
            for button in self.quick_buttons:
                button.state(["disabled"])
            return

        ip, mac, hostname, label = values
        self.selected_ip_var.set(ip)
        self.selected_mac_var.set(mac)
        self.selected_host_var.set(hostname or self._t("unknown"))
        self.selected_label_var.set(label or self._t("none"))
        self.detail_hint.configure(text=label or hostname or ip)
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
        super()._apply_language()
        self.discovery_title.configure(text=self._t("discovery"))
        self.discovery_hint.configure(text=self._t("discovery_hint"))
        self.devices_title.configure(text=self._t("devices"))
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

        self._on_device_selected()

    def _apply_theme(self) -> None:
        super()._apply_theme()
        style = ttk.Style(self)

        if self.theme == "dark":
            card = "#181d27"
            hero = "#16213a"
            detail = "#131925"
            fg = "#f5f7fb"
            muted = "#91a0b5"
            border = "#2b3342"
            hover = "#232b39"
        else:
            card = "#ffffff"
            hero = "#eaf1ff"
            detail = "#f7f9fc"
            fg = "#152033"
            muted = "#667085"
            border = "#dbe2ea"
            hover = "#eef2f7"

        style.configure("Hero.TFrame", background=hero)
        style.configure(
            "HeroTitle.TLabel",
            background=hero,
            foreground=fg,
            font=("Segoe UI Semibold", 15),
        )
        style.configure(
            "HeroSubtitle.TLabel",
            background=hero,
            foreground=muted,
            font=("Segoe UI", 9),
        )
        style.configure(
            "HeroField.TLabel",
            background=hero,
            foreground=muted,
            font=("Segoe UI Semibold", 9),
        )
        style.configure("Detail.TFrame", background=detail)
        style.configure(
            "DetailTitle.TLabel",
            background=detail,
            foreground=fg,
            font=("Segoe UI Semibold", 14),
        )
        style.configure(
            "DetailHint.TLabel",
            background=detail,
            foreground=muted,
            font=("Segoe UI", 9),
        )
        style.configure(
            "DetailKey.TLabel",
            background=detail,
            foreground=muted,
            font=("Segoe UI Semibold", 8),
        )
        style.configure(
            "DetailValue.TLabel",
            background=detail,
            foreground=fg,
            font=("Segoe UI", 10),
        )
        style.configure(
            "SectionTitle.TLabel",
            background=card,
            foreground=fg,
            font=("Segoe UI Semibold", 13),
        )
        style.configure(
            "Secondary.TButton",
            background=detail,
            foreground=fg,
            bordercolor=border,
            padding=(12, 8),
            font=("Segoe UI", 9),
        )
        style.map(
            "Secondary.TButton",
            background=[("active", hover), ("pressed", hover)],
        )


def main() -> None:
    app = ModernNetScanPyApp()
    app.mainloop()


if __name__ == "__main__":
    main()
