from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .gui import NetScanPyApp, TRANSLATIONS


EXTRA_TRANSLATIONS = {
    "fr": {
        "selected_device": "Appareil sélectionné",
        "quick_actions": "Actions",
        "search_label": "Rechercher",
    },
    "en": {
        "selected_device": "Selected device",
        "quick_actions": "Actions",
        "search_label": "Search",
    },
    "de": {
        "selected_device": "Ausgewähltes Gerät",
        "quick_actions": "Aktionen",
        "search_label": "Suchen",
    },
    "zh": {
        "selected_device": "已选设备",
        "quick_actions": "操作",
        "search_label": "搜索",
    },
}

for language, values in EXTRA_TRANSLATIONS.items():
    TRANSLATIONS.setdefault(language, {}).update(values)


class ModernNetScanPyApp(NetScanPyApp):
    def __init__(self) -> None:
        self.theme = "dark"
        super().__init__()
        self.theme = "dark"
        self.title("NetScanPy")
        self.geometry("1200x760")
        self.minsize(960, 620)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        # Header: only the product name and useful controls.
        self.header = ttk.Frame(self, style="Header.TFrame", padding=(24, 14))
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.columnconfigure(0, weight=1)

        self.brand_title = ttk.Label(
            self.header,
            text="NetScanPy",
            style="Brand.TLabel",
        )
        self.brand_title.grid(row=0, column=0, sticky="w")

        self.header_actions = ttk.Frame(self.header, style="Header.TFrame")
        self.header_actions.grid(row=0, column=1, sticky="e")

        # Scanner controls.
        self.scan_card = ttk.Frame(self, style="Card.TFrame", padding=(18, 16))
        self.scan_card.grid(row=1, column=0, sticky="ew", padx=24, pady=(18, 12))
        self.scan_card.columnconfigure(1, weight=1)

        self.network_label = ttk.Label(
            self.scan_card,
            text=self._t("network"),
            style="FieldLabel.TLabel",
        )
        self.network_label.grid(row=0, column=0, sticky="w", padx=(0, 12))

        self.network_entry = ttk.Entry(
            self.scan_card,
            textvariable=self.network_var,
            style="Modern.TEntry",
            font=("Segoe UI", 11),
        )
        self.network_entry.grid(row=0, column=1, sticky="ew", ipady=6)

        self.scan_button = ttk.Button(
            self.scan_card,
            text=self._t("scan"),
            command=self.start_scan,
            style="Accent.TButton",
        )
        self.scan_button.grid(row=0, column=2, padx=(12, 0), ipadx=16, ipady=4)

        # Useful information only.
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

        workspace = ttk.Frame(self, style="Root.TFrame")
        workspace.grid(row=3, column=0, sticky="nsew", padx=24, pady=(0, 20))
        workspace.columnconfigure(0, weight=1)
        workspace.columnconfigure(1, weight=0)
        workspace.rowconfigure(0, weight=1)

        # Device list.
        self.content_card = ttk.Frame(workspace, style="Card.TFrame", padding=(18, 16))
        self.content_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.content_card.columnconfigure(0, weight=1)
        self.content_card.rowconfigure(2, weight=1)

        top_row = ttk.Frame(self.content_card, style="Card.TFrame")
        top_row.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        top_row.columnconfigure(0, weight=1)

        self.devices_title = ttk.Label(
            top_row,
            text=self._t("devices"),
            style="SectionTitle.TLabel",
        )
        self.devices_title.grid(row=0, column=0, sticky="w")

        search_row = ttk.Frame(self.content_card, style="Card.TFrame")
        search_row.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        search_row.columnconfigure(1, weight=1)

        self.search_label = ttk.Label(
            search_row,
            text=self._t("search_label"),
            style="FieldLabel.TLabel",
        )
        self.search_label.grid(row=0, column=0, sticky="w", padx=(0, 10))

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

        self.tree.column("ip", width=145, minwidth=115, anchor="w")
        self.tree.column("mac", width=185, minwidth=150, anchor="w")
        self.tree.column("hostname", width=250, minwidth=160, anchor="w")
        self.tree.column("label", width=170, minwidth=115, anchor="w")

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

        # Device inspector.
        self.detail_card = ttk.Frame(
            workspace,
            style="Detail.TFrame",
            padding=(20, 18),
        )
        self.detail_card.grid(row=0, column=1, sticky="ns")
        self.detail_card.configure(width=300)
        self.detail_card.grid_propagate(False)
        self.detail_card.columnconfigure(0, weight=1)

        self.detail_title = ttk.Label(
            self.detail_card,
            text=self._t("selected_device"),
            style="DetailTitle.TLabel",
        )
        self.detail_title.grid(row=0, column=0, sticky="w", pady=(0, 16))

        self.selected_ip_var = tk.StringVar(value="—")
        self.selected_mac_var = tk.StringVar(value="—")
        self.selected_host_var = tk.StringVar(value="—")
        self.selected_label_var = tk.StringVar(value="—")

        self.detail_value_labels: list[ttk.Label] = []
        row = 1
        for key, variable in (
            ("ip", self.selected_ip_var),
            ("mac", self.selected_mac_var),
            ("hostname", self.selected_host_var),
            ("label", self.selected_label_var),
        ):
            label = ttk.Label(
                self.detail_card,
                text=self._t(key),
                style="DetailKey.TLabel",
            )
            label.grid(row=row, column=0, sticky="w", pady=(0, 3))

            value = ttk.Label(
                self.detail_card,
                textvariable=variable,
                style="DetailValue.TLabel",
                wraplength=255,
            )
            value.grid(row=row + 1, column=0, sticky="w", pady=(0, 13))
            self.detail_value_labels.append(label)
            row += 2

        ttk.Separator(self.detail_card, orient="horizontal").grid(
            row=row,
            column=0,
            sticky="ew",
            pady=(4, 14),
        )
        row += 1

        self.quick_actions_label = ttk.Label(
            self.detail_card,
            text=self._t("quick_actions"),
            style="DetailKey.TLabel",
        )
        self.quick_actions_label.grid(row=row, column=0, sticky="w", pady=(0, 8))
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

        self.devices_card._title_label.configure(text=self._t("devices"))  # type: ignore[attr-defined]
        self.network_card._title_label.configure(text=self._t("current_network"))  # type: ignore[attr-defined]
        self.status_card._title_label.configure(text=self._t("status"))  # type: ignore[attr-defined]
        self.count_var.set(self._t("device_count", count=len(self.devices)))

        if self.status_var.get() in ("Ready", "Prêt", "Bereit", "就绪"):
            self.status_var.set(self._t("ready"))

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

    def _apply_theme(self) -> None:
        self.theme = "dark"
        super()._apply_theme()
        style = ttk.Style(self)

        root = "#0a0d12"
        header = "#0d1117"
        card = "#11161f"
        raised = "#151b25"
        field = "#0c1118"
        detail = "#0f141c"
        border = "#252d3a"
        fg = "#f2f5f8"
        muted = "#7f8b9d"
        accent = "#4f8cff"
        accent_hover = "#6c9fff"
        selected = "#17345f"
        hover = "#1b2431"

        self.configure(bg=root)

        style.configure("Root.TFrame", background=root)
        style.configure("Header.TFrame", background=header)
        style.configure("Card.TFrame", background=card)
        style.configure("Detail.TFrame", background=detail)
        style.configure("Table.TFrame", background=border)

        style.configure(
            "Brand.TLabel",
            background=header,
            foreground=fg,
            font=("Segoe UI Semibold", 19),
        )
        style.configure(
            "FieldLabel.TLabel",
            background=card,
            foreground=muted,
            font=("Segoe UI Semibold", 9),
        )
        style.configure(
            "SectionTitle.TLabel",
            background=card,
            foreground=fg,
            font=("Segoe UI Semibold", 14),
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
        style.configure(
            "DetailTitle.TLabel",
            background=detail,
            foreground=fg,
            font=("Segoe UI Semibold", 14),
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
            "Accent.TButton",
            background=accent,
            foreground="#ffffff",
            bordercolor=accent,
            padding=(14, 9),
            font=("Segoe UI Semibold", 10),
        )
        style.map(
            "Accent.TButton",
            background=[("active", accent_hover), ("pressed", accent_hover)],
            foreground=[("disabled", "#6e7785")],
        )

        style.configure(
            "Secondary.TButton",
            background=raised,
            foreground=fg,
            bordercolor=border,
            padding=(12, 8),
            font=("Segoe UI", 9),
        )
        style.map(
            "Secondary.TButton",
            background=[("active", hover), ("pressed", hover)],
            foreground=[("disabled", "#616b79")],
        )

        style.configure(
            "Header.TMenubutton",
            background=header,
            foreground=muted,
            bordercolor=border,
            padding=(12, 7),
            font=("Segoe UI", 9),
        )
        style.map(
            "Header.TMenubutton",
            background=[("active", hover), ("pressed", hover)],
            foreground=[("active", fg)],
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
            background=raised,
            foreground="#a6b0bf",
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

        for menu in (self.language_menu, self.interface_menu, self.context_menu):
            menu.configure(
                background=raised,
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
