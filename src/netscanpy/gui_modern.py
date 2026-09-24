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
        "discovery_hint": "Détecte les appareils de ton réseau local et accède rapidement aux outils utiles.",
        "search_label": "Filtrer les appareils",
        "devices_found": "Appareils détectés",
        "network_overview": "Vue réseau",
        "scanner_ready": "SCANNER PRÊT",
    },
    "en": {
        "selected_device": "Selected device",
        "select_device_hint": "Select a device to view its information and quick actions.",
        "quick_actions": "Quick actions",
        "discovery": "Network discovery",
        "discovery_hint": "Detect devices on your local network and quickly access useful tools.",
        "search_label": "Filter devices",
        "devices_found": "Detected devices",
        "network_overview": "Network overview",
        "scanner_ready": "SCANNER READY",
    },
    "de": {
        "selected_device": "Ausgewähltes Gerät",
        "select_device_hint": "Wähle ein Gerät aus, um Informationen und Schnellaktionen anzuzeigen.",
        "quick_actions": "Schnellaktionen",
        "discovery": "Netzwerkerkennung",
        "discovery_hint": "Erkenne Geräte im lokalen Netzwerk und greife schnell auf nützliche Werkzeuge zu.",
        "search_label": "Geräte filtern",
        "devices_found": "Erkannte Geräte",
        "network_overview": "Netzwerkübersicht",
        "scanner_ready": "SCANNER BEREIT",
    },
    "zh": {
        "selected_device": "已选设备",
        "select_device_hint": "选择设备后可查看信息并使用快捷操作。",
        "quick_actions": "快捷操作",
        "discovery": "网络发现",
        "discovery_hint": "检测本地网络设备并快速使用常用工具。",
        "search_label": "筛选设备",
        "devices_found": "检测到的设备",
        "network_overview": "网络概览",
        "scanner_ready": "扫描器已就绪",
    },
}

for language, values in EXTRA_TRANSLATIONS.items():
    TRANSLATIONS.setdefault(language, {}).update(values)


class ModernNetScanPyApp(NetScanPyApp):
    """Dark-only NetScanPy desktop interface."""

    def __init__(self) -> None:
        # The application is intentionally dark-only.  Keeping this value fixed
        # also makes the native Windows title bar consistently dark.
        self.theme = "dark"
        super().__init__()
        self.theme = "dark"
        self.title("NetScanPy")
        self.geometry("1240x780")
        self.minsize(980, 640)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        # Top application bar.
        self.header = ttk.Frame(self, style="Header.TFrame", padding=(28, 15))
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.columnconfigure(0, weight=1)

        brand = ttk.Frame(self.header, style="Header.TFrame")
        brand.grid(row=0, column=0, sticky="w")

        title_row = ttk.Frame(brand, style="Header.TFrame")
        title_row.pack(anchor="w")
        self.brand_title = ttk.Label(title_row, text="NetScanPy", style="Brand.TLabel")
        self.brand_title.pack(side="left")
        self.ready_badge = ttk.Label(
            title_row, text=self._t("scanner_ready"), style="ReadyBadge.TLabel"
        )
        self.ready_badge.pack(side="left", padx=(12, 0))

        self.brand_subtitle = ttk.Label(
            brand, text=self._t("app_subtitle"), style="Subtitle.TLabel"
        )
        self.brand_subtitle.pack(anchor="w", pady=(2, 0))

        self.header_actions = ttk.Frame(self.header, style="Header.TFrame")
        self.header_actions.grid(row=0, column=1, sticky="e")

        # Main scan panel.
        self.scan_card = ttk.Frame(self, style="Hero.TFrame", padding=(24, 22))
        self.scan_card.grid(row=1, column=0, sticky="ew", padx=26, pady=(20, 14))
        self.scan_card.columnconfigure(1, weight=1)

        hero_text = ttk.Frame(self.scan_card, style="Hero.TFrame")
        hero_text.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 34))
        self.discovery_title = ttk.Label(
            hero_text, text=self._t("discovery"), style="HeroTitle.TLabel"
        )
        self.discovery_title.pack(anchor="w")
        self.discovery_hint = ttk.Label(
            hero_text,
            text=self._t("discovery_hint"),
            style="HeroSubtitle.TLabel",
            wraplength=350,
        )
        self.discovery_hint.pack(anchor="w", pady=(6, 0))

        self.network_label = ttk.Label(
            self.scan_card, text=self._t("network"), style="HeroField.TLabel"
        )
        self.network_label.grid(row=0, column=1, sticky="w", pady=(0, 7))

        self.network_entry = ttk.Entry(
            self.scan_card,
            textvariable=self.network_var,
            style="Modern.TEntry",
            font=("Segoe UI", 11),
        )
        self.network_entry.grid(row=1, column=1, sticky="ew", ipady=6)

        self.scan_button = ttk.Button(
            self.scan_card,
            text=self._t("scan"),
            command=self.start_scan,
            style="Accent.TButton",
        )
        self.scan_button.grid(row=1, column=2, padx=(12, 0), ipadx=18, ipady=4)

        # Dashboard counters.
        self.stats = ttk.Frame(self, style="Root.TFrame")
        self.stats.grid(row=2, column=0, sticky="ew", padx=26, pady=(0, 14))
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

        # Main workspace.
        workspace = ttk.Frame(self, style="Root.TFrame")
        workspace.grid(row=3, column=0, sticky="nsew", padx=26, pady=(0, 22))
        workspace.columnconfigure(0, weight=1)
        workspace.columnconfigure(1, weight=0)
        workspace.rowconfigure(0, weight=1)

        self.content_card = ttk.Frame(workspace, style="Card.TFrame", padding=(20, 18))
        self.content_card.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        self.content_card.columnconfigure(0, weight=1)
        self.content_card.rowconfigure(2, weight=1)

        list_header = ttk.Frame(self.content_card, style="Card.TFrame")
        list_header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        list_header.columnconfigure(0, weight=1)

        heading = ttk.Frame(list_header, style="Card.TFrame")
        heading.grid(row=0, column=0, sticky="w")
        self.devices_title = ttk.Label(
            heading, text=self._t("devices_found"), style="SectionTitle.TLabel"
        )
        self.devices_title.pack(anchor="w")
        self.devices_caption = ttk.Label(
            heading, text=self._t("network_overview"), style="SectionHint.TLabel"
        )
        self.devices_caption.pack(anchor="w", pady=(2, 0))

        search_row = ttk.Frame(self.content_card, style="Card.TFrame")
        search_row.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        search_row.columnconfigure(1, weight=1)
        self.search_label = ttk.Label(
            search_row, text=self._t("search_label"), style="FieldLabel.TLabel"
        )
        self.search_label.grid(row=0, column=0, sticky="w", padx=(0, 12))
        self.search_entry = ttk.Entry(
            search_row,
            textvariable=self.search_var,
            style="Search.TEntry",
            font=("Segoe UI", 10),
        )
        self.search_entry.grid(row=0, column=1, sticky="ew", ipady=5)

        table_wrap = ttk.Frame(self.content_card, style="Table.TFrame", padding=1)
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
        self.tree.column("ip", width=140, minwidth=115, anchor="w")
        self.tree.column("mac", width=180, minwidth=150, anchor="w")
        self.tree.column("hostname", width=250, minwidth=160, anchor="w")
        self.tree.column("label", width=160, minwidth=115, anchor="w")

        scrollbar = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.progress = ttk.Progressbar(
            self.content_card,
            mode="indeterminate",
            style="Accent.Horizontal.TProgressbar",
        )
        self.progress.grid(row=3, column=0, sticky="ew", pady=(14, 0))

        # Device inspector.
        self.detail_card = ttk.Frame(workspace, style="Detail.TFrame", padding=(22, 20))
        self.detail_card.grid(row=0, column=1, sticky="ns", ipadx=4)
        self.detail_card.configure(width=310)
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
            wraplength=260,
            justify="left",
        )
        self.detail_hint.grid(row=1, column=0, sticky="ew", pady=(7, 20))

        ttk.Separator(self.detail_card, orient="horizontal").grid(
            row=2, column=0, sticky="ew", pady=(0, 18)
        )

        self.selected_ip_var = tk.StringVar(value="—")
        self.selected_mac_var = tk.StringVar(value="—")
        self.selected_host_var = tk.StringVar(value="—")
        self.selected_label_var = tk.StringVar(value="—")

        self.detail_value_labels: list[ttk.Label] = []
        row = 3
        for key, variable in (
            ("ip", self.selected_ip_var),
            ("mac", self.selected_mac_var),
            ("hostname", self.selected_host_var),
            ("label", self.selected_label_var),
        ):
            label = ttk.Label(
                self.detail_card, text=self._t(key), style="DetailKey.TLabel"
            )
            label.grid(row=row, column=0, sticky="w", pady=(0, 3))
            value = ttk.Label(
                self.detail_card,
                textvariable=variable,
                style="DetailValue.TLabel",
                wraplength=260,
            )
            value.grid(row=row + 1, column=0, sticky="w", pady=(0, 13))
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

    def _build_menus(self) -> None:
        """Build only the language menu; there is no light-theme control."""
        self.language_menu = tk.Menu(self, tearoff=False)
        # Kept as an empty menu because the shared base styling code themes it.
        # It is never displayed and contains no light-theme action.
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
        """NetScanPy uses one visual identity: dark."""
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
        # Reimplements the base language refresh without the removed interface menu.
        self.brand_subtitle.configure(text=self._t("app_subtitle"))
        self.network_label.configure(text=self._t("network"))
        self.scan_button.configure(text=self._t("scan"))
        self.language_button.configure(text=self._t("language"))
        self.ready_badge.configure(text=self._t("scanner_ready"))

        self.tree.heading("ip", text=self._t("ip"))
        self.tree.heading("mac", text=self._t("mac"))
        self.tree.heading("hostname", text=self._t("hostname"))
        self.tree.heading("label", text=self._t("label"))
        self._populate_context_menu()

        self.devices_card._title_label.configure(text=self._t("devices"))  # type: ignore[attr-defined]
        self.network_card._title_label.configure(text=self._t("current_network"))  # type: ignore[attr-defined]
        self.status_card._title_label.configure(text=self._t("status"))  # type: ignore[attr-defined]
        self.count_var.set(self._t("device_count", count=len(self.devices)))

        if self.status_var.get() in ("Ready", "Prêt", "Bereit", "就绪"):
            self.status_var.set(self._t("ready"))

        self.discovery_title.configure(text=self._t("discovery"))
        self.discovery_hint.configure(text=self._t("discovery_hint"))
        self.devices_title.configure(text=self._t("devices_found"))
        self.devices_caption.configure(text=self._t("network_overview"))
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
        # Force dark before invoking the shared widget theme definitions.
        self.theme = "dark"
        super()._apply_theme()
        style = ttk.Style(self)

        root = "#090d14"
        header = "#0d121c"
        card = "#111824"
        card_raised = "#151e2c"
        hero = "#101d33"
        detail = "#0e1622"
        field = "#0b111b"
        fg = "#f4f7fb"
        muted = "#8290a5"
        border = "#253147"
        accent = "#4f8cff"
        accent_hover = "#6ba0ff"
        hover = "#1b2738"
        selected = "#17335d"
        success = "#6ee7b7"

        self.configure(bg=root)
        style.configure("Root.TFrame", background=root)
        style.configure("Header.TFrame", background=header)
        style.configure("Card.TFrame", background=card)
        style.configure("Table.TFrame", background=border)

        style.configure(
            "Brand.TLabel",
            background=header,
            foreground=fg,
            font=("Segoe UI Semibold", 19),
        )
        style.configure(
            "Subtitle.TLabel",
            background=header,
            foreground=muted,
            font=("Segoe UI", 9),
        )
        style.configure(
            "ReadyBadge.TLabel",
            background=header,
            foreground=success,
            font=("Segoe UI Semibold", 8),
            padding=(8, 3),
        )
        style.configure(
            "Header.TMenubutton",
            background=card,
            foreground=fg,
            bordercolor=border,
            lightcolor=border,
            darkcolor=border,
            padding=(13, 8),
            font=("Segoe UI", 9),
        )
        style.map(
            "Header.TMenubutton",
            background=[("active", hover), ("pressed", hover)],
        )

        style.configure("Hero.TFrame", background=hero)
        style.configure(
            "HeroTitle.TLabel",
            background=hero,
            foreground=fg,
            font=("Segoe UI Semibold", 17),
        )
        style.configure(
            "HeroSubtitle.TLabel",
            background=hero,
            foreground="#9badc7",
            font=("Segoe UI", 9),
        )
        style.configure(
            "HeroField.TLabel",
            background=hero,
            foreground="#9badc7",
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
            padding=(11, 9),
        )
        style.configure(
            "Search.TEntry",
            fieldbackground=field,
            foreground=fg,
            insertcolor=fg,
            bordercolor=border,
            lightcolor=border,
            darkcolor=border,
            padding=(11, 9),
        )

        style.configure(
            "StatTitle.TLabel",
            background=card,
            foreground=muted,
            font=("Segoe UI Semibold", 8),
        )
        style.configure(
            "StatValue.TLabel",
            background=card,
            foreground=fg,
            font=("Segoe UI Semibold", 13),
        )

        style.configure("Detail.TFrame", background=detail)
        style.configure(
            "DetailTitle.TLabel",
            background=detail,
            foreground=fg,
            font=("Segoe UI Semibold", 15),
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
            font=("Segoe UI Semibold", 14),
        )
        style.configure(
            "SectionHint.TLabel",
            background=card,
            foreground=muted,
            font=("Segoe UI", 9),
        )
        style.configure(
            "FieldLabel.TLabel",
            background=card,
            foreground=muted,
            font=("Segoe UI Semibold", 9),
        )

        style.configure(
            "Accent.TButton",
            background=accent,
            foreground="#ffffff",
            bordercolor=accent,
            lightcolor=accent,
            darkcolor=accent,
            padding=(14, 9),
            font=("Segoe UI Semibold", 10),
        )
        style.map(
            "Accent.TButton",
            background=[("active", accent_hover), ("pressed", accent_hover)],
            foreground=[("disabled", "#738096")],
        )
        style.configure(
            "Secondary.TButton",
            background=card_raised,
            foreground=fg,
            bordercolor=border,
            lightcolor=border,
            darkcolor=border,
            padding=(12, 8),
            font=("Segoe UI", 9),
        )
        style.map(
            "Secondary.TButton",
            background=[("active", hover), ("pressed", hover)],
            foreground=[("disabled", "#667085")],
        )

        style.configure(
            "Modern.Treeview",
            background=field,
            fieldbackground=field,
            foreground=fg,
            bordercolor=border,
            rowheight=38,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Modern.Treeview.Heading",
            background=card_raised,
            foreground="#a9b5c7",
            bordercolor=border,
            padding=(9, 10),
            font=("Segoe UI Semibold", 9),
        )
        style.map(
            "Modern.Treeview",
            background=[("selected", selected)],
            foreground=[("selected", "#ffffff")],
        )
        style.map(
            "Modern.Treeview.Heading",
            background=[("active", hover)],
        )

        style.configure(
            "Accent.Horizontal.TProgressbar",
            troughcolor=field,
            background=accent,
            bordercolor=field,
            lightcolor=accent,
            darkcolor=accent,
        )
        style.configure("TSeparator", background=border)

        # Native Tk menus also stay dark.
        for menu in (self.language_menu, self.interface_menu, self.context_menu):
            menu.configure(
                background=card_raised,
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
