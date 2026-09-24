from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from tkinter import ttk

from .gui import NetScanPyApp, TRANSLATIONS
from .network_info import (
    PublicNetworkInfo,
    fetch_public_network_info,
    get_local_network_info,
)


EXTRA_TRANSLATIONS = {
    "fr": {
        "selected_device": "Appareil",
        "quick_actions": "Actions",
        "search_label": "Rechercher",
        "inventory": "Inventaire réseau",
        "devices_online": "Appareils",
        "device_tab": "Appareil",
        "network_tab": "Réseau",
        "local_network": "Réseau local",
        "internet_connection": "Connexion Internet",
        "interface_name": "Interface",
        "local_ip": "IP locale",
        "netmask": "Masque",
        "subnet": "Sous-réseau",
        "public_ip": "IP publique",
        "location": "Localisation",
        "coordinates": "Coordonnées",
        "operator": "Opérateur / organisation",
        "asn": "ASN",
        "timezone": "Fuseau horaire",
        "postal": "Code postal",
        "currency": "Devise",
        "languages": "Langues",
        "refresh_info": "Actualiser",
        "open_map": "Ouvrir la carte",
        "copy_public_ip": "Copier l’IP publique",
        "loading": "Chargement…",
        "unavailable": "Indisponible",
        "geo_note": "La géolocalisation IP est approximative et concerne l’IP publique.",
    },
    "en": {
        "selected_device": "Device",
        "quick_actions": "Actions",
        "search_label": "Search",
        "inventory": "Network inventory",
        "devices_online": "Devices",
        "device_tab": "Device",
        "network_tab": "Network",
        "local_network": "Local network",
        "internet_connection": "Internet connection",
        "interface_name": "Interface",
        "local_ip": "Local IP",
        "netmask": "Netmask",
        "subnet": "Subnet",
        "public_ip": "Public IP",
        "location": "Location",
        "coordinates": "Coordinates",
        "operator": "Operator / organization",
        "asn": "ASN",
        "timezone": "Timezone",
        "postal": "Postal code",
        "currency": "Currency",
        "languages": "Languages",
        "refresh_info": "Refresh",
        "open_map": "Open map",
        "copy_public_ip": "Copy public IP",
        "loading": "Loading…",
        "unavailable": "Unavailable",
        "geo_note": "IP geolocation is approximate and applies to the public IP address.",
    },
    "de": {
        "selected_device": "Gerät",
        "quick_actions": "Aktionen",
        "search_label": "Suchen",
        "inventory": "Netzwerkinventar",
        "devices_online": "Geräte",
        "device_tab": "Gerät",
        "network_tab": "Netzwerk",
        "local_network": "Lokales Netzwerk",
        "internet_connection": "Internetverbindung",
        "interface_name": "Schnittstelle",
        "local_ip": "Lokale IP",
        "netmask": "Netzmaske",
        "subnet": "Subnetz",
        "public_ip": "Öffentliche IP",
        "location": "Standort",
        "coordinates": "Koordinaten",
        "operator": "Provider / Organisation",
        "asn": "ASN",
        "timezone": "Zeitzone",
        "postal": "Postleitzahl",
        "currency": "Währung",
        "languages": "Sprachen",
        "refresh_info": "Aktualisieren",
        "open_map": "Karte öffnen",
        "copy_public_ip": "Öffentliche IP kopieren",
        "loading": "Wird geladen…",
        "unavailable": "Nicht verfügbar",
        "geo_note": "Die IP-Geolokalisierung ist ungefähr und bezieht sich auf die öffentliche IP.",
    },
    "zh": {
        "selected_device": "设备",
        "quick_actions": "操作",
        "search_label": "搜索",
        "inventory": "网络资产",
        "devices_online": "设备",
        "device_tab": "设备",
        "network_tab": "网络",
        "local_network": "本地网络",
        "internet_connection": "互联网连接",
        "interface_name": "接口",
        "local_ip": "本地 IP",
        "netmask": "子网掩码",
        "subnet": "子网",
        "public_ip": "公网 IP",
        "location": "位置",
        "coordinates": "坐标",
        "operator": "运营商 / 组织",
        "asn": "ASN",
        "timezone": "时区",
        "postal": "邮政编码",
        "currency": "货币",
        "languages": "语言",
        "refresh_info": "刷新",
        "open_map": "打开地图",
        "copy_public_ip": "复制公网 IP",
        "loading": "加载中…",
        "unavailable": "不可用",
        "geo_note": "IP 地理位置是近似值，仅对应公网 IP。",
    },
}

for language, values in EXTRA_TRANSLATIONS.items():
    TRANSLATIONS.setdefault(language, {}).update(values)


class ModernNetScanPyApp(NetScanPyApp):
    """Dark enterprise-style network console with local and public network intelligence."""

    def __init__(self) -> None:
        self.theme = "dark"
        self.public_network_info: PublicNetworkInfo | None = None
        super().__init__()
        self.theme = "dark"
        self.title("NetScanPy")
        self.geometry("1340x820")
        self.minsize(1080, 680)
        self.after(150, self.refresh_network_intelligence)

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

        # Compact status line.
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

        ttk.Separator(self.summary_bar, orient="vertical").pack(
            side="left", fill="y", padx=(0, 22)
        )

        self.summary_network_title = ttk.Label(
            self.summary_bar, text=self._t("current_network"), style="SummaryKey.TLabel"
        )
        self.summary_network_title.pack(side="left")
        self.summary_network_value = ttk.Label(
            self.summary_bar, textvariable=self.network_stat_var, style="SummaryValue.TLabel"
        )
        self.summary_network_value.pack(side="left", padx=(7, 22))

        ttk.Separator(self.summary_bar, orient="vertical").pack(
            side="left", fill="y", padx=(0, 22)
        )

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

        # Main network inventory.
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

        # Enterprise-style inspector with separate device and network tabs.
        self.inspector = ttk.Frame(workspace, style="Inspector.TFrame")
        self.inspector.grid(row=0, column=1, sticky="ns")
        self.inspector.configure(width=370)
        self.inspector.grid_propagate(False)
        self.inspector.rowconfigure(0, weight=1)
        self.inspector.columnconfigure(0, weight=1)

        self.inspector_tabs = ttk.Notebook(self.inspector, style="Enterprise.TNotebook")
        self.inspector_tabs.grid(row=0, column=0, sticky="nsew")

        self.device_tab = ttk.Frame(self.inspector_tabs, style="Inspector.TFrame")
        self.network_info_tab = ttk.Frame(self.inspector_tabs, style="Inspector.TFrame")
        self.inspector_tabs.add(self.device_tab, text=self._t("device_tab"))
        self.inspector_tabs.add(self.network_info_tab, text=self._t("network_tab"))

        self._build_device_tab()
        self._build_network_info_tab()

        self.context_menu = tk.Menu(self, tearoff=False)
        self._populate_context_menu()
        self.tree.bind("<ButtonRelease-3>", self._show_context_menu)
        self.tree.bind("<Shift-F10>", self._show_context_menu_keyboard)
        self.tree.bind("<Double-1>", lambda _e: self.show_details_selected())
        self.tree.bind("<<TreeviewSelect>>", self._on_device_selected)

    def _build_device_tab(self) -> None:
        self.device_tab.columnconfigure(0, weight=1)

        body = ttk.Frame(self.device_tab, style="Inspector.TFrame", padding=(20, 18))
        body.grid(row=0, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)

        self.detail_title = ttk.Label(
            body, text=self._t("selected_device"), style="InspectorTitle.TLabel"
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
            key_label = ttk.Label(body, text=self._t(key), style="InspectorKey.TLabel")
            key_label.grid(row=row, column=0, sticky="w")
            value_label = ttk.Label(
                body,
                textvariable=variable,
                style="InspectorValue.TLabel",
                wraplength=315,
            )
            value_label.grid(row=row + 1, column=0, sticky="w", pady=(3, 15))
            self.detail_value_labels.append(key_label)
            row += 2

        ttk.Separator(body, orient="horizontal").grid(
            row=row, column=0, sticky="ew", pady=(2, 15)
        )
        row += 1

        self.quick_actions_label = ttk.Label(
            body, text=self._t("quick_actions"), style="InspectorKey.TLabel"
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
            button = ttk.Button(body, text=self._t(text_key), command=command, style=style_name)
            button.grid(row=row, column=0, sticky="ew", pady=3)
            button.state(["disabled"])
            self.quick_buttons.append(button)
            row += 1

    def _build_network_info_tab(self) -> None:
        self.network_info_tab.columnconfigure(0, weight=1)

        body = ttk.Frame(self.network_info_tab, style="Inspector.TFrame", padding=(20, 18))
        body.grid(row=0, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        self.local_section_title = ttk.Label(
            body, text=self._t("local_network"), style="InspectorTitle.TLabel"
        )
        self.local_section_title.grid(row=0, column=0, sticky="w")

        self.refresh_info_button = ttk.Button(
            body,
            text=self._t("refresh_info"),
            command=self.refresh_network_intelligence,
            style="Compact.TButton",
        )
        self.refresh_info_button.grid(row=0, column=1, sticky="e")

        self.local_interface_var = tk.StringVar(value="—")
        self.local_ip_var = tk.StringVar(value="—")
        self.local_netmask_var = tk.StringVar(value="—")
        self.local_subnet_var = tk.StringVar(value="—")

        self.local_info_labels: list[ttk.Label] = []
        row = 1
        for key, variable in (
            ("interface_name", self.local_interface_var),
            ("local_ip", self.local_ip_var),
            ("netmask", self.local_netmask_var),
            ("subnet", self.local_subnet_var),
        ):
            label = ttk.Label(body, text=self._t(key), style="InspectorKey.TLabel")
            label.grid(row=row, column=0, columnspan=2, sticky="w", pady=(14 if row == 1 else 0, 0))
            ttk.Label(
                body,
                textvariable=variable,
                style="InspectorValue.TLabel",
                wraplength=315,
            ).grid(row=row + 1, column=0, columnspan=2, sticky="w", pady=(3, 10))
            self.local_info_labels.append(label)
            row += 2

        ttk.Separator(body, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=(5, 15)
        )
        row += 1

        self.internet_section_title = ttk.Label(
            body, text=self._t("internet_connection"), style="InspectorTitle.TLabel"
        )
        self.internet_section_title.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 8))
        row += 1

        self.public_ip_var = tk.StringVar(value="—")
        self.location_var = tk.StringVar(value="—")
        self.coordinates_var = tk.StringVar(value="—")
        self.operator_var = tk.StringVar(value="—")
        self.asn_var = tk.StringVar(value="—")
        self.timezone_var = tk.StringVar(value="—")
        self.postal_var = tk.StringVar(value="—")
        self.currency_var = tk.StringVar(value="—")
        self.languages_var = tk.StringVar(value="—")

        self.public_info_labels: list[ttk.Label] = []
        public_fields = (
            ("public_ip", self.public_ip_var),
            ("location", self.location_var),
            ("coordinates", self.coordinates_var),
            ("operator", self.operator_var),
            ("asn", self.asn_var),
            ("timezone", self.timezone_var),
            ("postal", self.postal_var),
            ("currency", self.currency_var),
            ("languages", self.languages_var),
        )
        for key, variable in public_fields:
            label = ttk.Label(body, text=self._t(key), style="InspectorKey.TLabel")
            label.grid(row=row, column=0, columnspan=2, sticky="w")
            ttk.Label(
                body,
                textvariable=variable,
                style="InspectorValue.TLabel",
                wraplength=315,
            ).grid(row=row + 1, column=0, columnspan=2, sticky="w", pady=(3, 9))
            self.public_info_labels.append(label)
            row += 2

        self.copy_public_ip_button = ttk.Button(
            body,
            text=self._t("copy_public_ip"),
            command=self.copy_public_ip,
            style="Inspector.TButton",
        )
        self.copy_public_ip_button.grid(row=row, column=0, sticky="ew", padx=(0, 4), pady=(4, 8))

        self.open_map_button = ttk.Button(
            body,
            text=self._t("open_map"),
            command=self.open_public_ip_map,
            style="Inspector.TButton",
        )
        self.open_map_button.grid(row=row, column=1, sticky="ew", padx=(4, 0), pady=(4, 8))
        row += 1

        self.geo_note_label = ttk.Label(
            body,
            text=self._t("geo_note"),
            style="InspectorNote.TLabel",
            wraplength=315,
            justify="left",
        )
        self.geo_note_label.grid(row=row, column=0, columnspan=2, sticky="ew")

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

    def refresh_network_intelligence(self) -> None:
        local = get_local_network_info()
        if local is None:
            unavailable = self._t("unavailable")
            self.local_interface_var.set(unavailable)
            self.local_ip_var.set(unavailable)
            self.local_netmask_var.set(unavailable)
            self.local_subnet_var.set(unavailable)
        else:
            self.local_interface_var.set(local.interface)
            self.local_ip_var.set(local.ip)
            self.local_netmask_var.set(local.netmask)
            self.local_subnet_var.set(f"{local.network}  /{local.prefix_length}")

        loading = self._t("loading")
        for variable in (
            self.public_ip_var,
            self.location_var,
            self.coordinates_var,
            self.operator_var,
            self.asn_var,
            self.timezone_var,
            self.postal_var,
            self.currency_var,
            self.languages_var,
        ):
            variable.set(loading)

        self.refresh_info_button.state(["disabled"])
        threading.Thread(target=self._load_public_network_info, daemon=True).start()

    def _load_public_network_info(self) -> None:
        try:
            info = fetch_public_network_info()
        except RuntimeError:
            self.after(0, self._set_public_network_unavailable)
            return
        self.after(0, lambda: self._apply_public_network_info(info))

    def _set_public_network_unavailable(self) -> None:
        unavailable = self._t("unavailable")
        for variable in (
            self.public_ip_var,
            self.location_var,
            self.coordinates_var,
            self.operator_var,
            self.asn_var,
            self.timezone_var,
            self.postal_var,
            self.currency_var,
            self.languages_var,
        ):
            variable.set(unavailable)
        self.public_network_info = None
        self.refresh_info_button.state(["!disabled"])

    def _apply_public_network_info(self, info: PublicNetworkInfo) -> None:
        self.public_network_info = info
        self.public_ip_var.set(info.ip)
        location_parts = [part for part in (info.city, info.region, info.country) if part != "—"]
        self.location_var.set(", ".join(location_parts) or "—")
        self.coordinates_var.set(f"{info.latitude}, {info.longitude}")
        self.operator_var.set(info.organization)
        self.asn_var.set(info.asn)
        timezone = info.timezone
        if info.utc_offset != "—":
            timezone = f"{timezone} ({info.utc_offset})"
        self.timezone_var.set(timezone)
        self.postal_var.set(info.postal)
        self.currency_var.set(info.currency)
        self.languages_var.set(info.languages)
        self.refresh_info_button.state(["!disabled"])

    def copy_public_ip(self) -> None:
        value = self.public_ip_var.get()
        if value in ("", "—", self._t("loading"), self._t("unavailable")):
            return
        self.clipboard_clear()
        self.clipboard_append(value)
        self.update_idletasks()

    def open_public_ip_map(self) -> None:
        info = self.public_network_info
        if info is None or info.latitude == "—" or info.longitude == "—":
            return
        webbrowser.open(
            f"https://www.openstreetmap.org/?mlat={info.latitude}&mlon={info.longitude}"
            f"#map=12/{info.latitude}/{info.longitude}"
        )

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

        self.inspector_tabs.tab(self.device_tab, text=self._t("device_tab"))
        self.inspector_tabs.tab(self.network_info_tab, text=self._t("network_tab"))
        self.local_section_title.configure(text=self._t("local_network"))
        self.internet_section_title.configure(text=self._t("internet_connection"))
        self.refresh_info_button.configure(text=self._t("refresh_info"))
        self.copy_public_ip_button.configure(text=self._t("copy_public_ip"))
        self.open_map_button.configure(text=self._t("open_map"))
        self.geo_note_label.configure(text=self._t("geo_note"))

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

        for label, key in zip(
            self.local_info_labels,
            ("interface_name", "local_ip", "netmask", "subnet"),
        ):
            label.configure(text=self._t(key))

        for label, key in zip(
            self.public_info_labels,
            (
                "public_ip",
                "location",
                "coordinates",
                "operator",
                "asn",
                "timezone",
                "postal",
                "currency",
                "languages",
            ),
        ):
            label.configure(text=self._t(key))

    def _apply_theme(self) -> None:
        self.theme = "dark"
        super()._apply_theme()
        style = ttk.Style(self)

        root = "#0a0e13"
        header = "#0c1118"
        surface = "#111821"
        inspector = "#0f161f"
        field = "#0b1118"
        border = "#2b3746"
        border_soft = "#202a36"
        fg = "#f0f4f8"
        muted = "#9aa8ba"
        accent = "#3b82f6"
        accent_hover = "#5a97f7"
        selected = "#173d6d"
        hover = "#1a2634"
        status = "#7ee2a8"

        self.configure(bg=root)

        style.configure("Root.TFrame", background=root)
        style.configure("Header.TFrame", background=header)
        style.configure("Command.TFrame", background=surface)
        style.configure("Summary.TFrame", background="#0d141c")
        style.configure("Panel.TFrame", background=surface)
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
            foreground="#c0cad6",
            bordercolor=border_soft,
            padding=(11, 6),
            font=("Segoe UI", 9),
        )
        style.map(
            "Header.TMenubutton",
            background=[("active", hover), ("pressed", hover)],
            foreground=[("active", "#ffffff")],
        )

        style.configure(
            "CommandLabel.TLabel",
            background=surface,
            foreground="#b1bdca",
            font=("Segoe UI Semibold", 9),
        )
        style.configure(
            "Modern.TEntry",
            fieldbackground=field,
            foreground="#ffffff",
            insertcolor="#ffffff",
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
            padding=(14, 7),
            font=("Segoe UI Semibold", 9),
        )
        style.map("Accent.TButton", background=[("active", accent_hover), ("pressed", accent_hover)])

        style.configure(
            "SummaryKey.TLabel",
            background="#0d141c",
            foreground="#98a7b8",
            font=("Segoe UI", 8),
        )
        style.configure(
            "SummaryValue.TLabel",
            background="#0d141c",
            foreground="#edf3f9",
            font=("Segoe UI Semibold", 8),
        )
        style.configure(
            "StatusValue.TLabel",
            background="#0d141c",
            foreground=status,
            font=("Segoe UI Semibold", 8),
        )

        style.configure(
            "SectionTitle.TLabel",
            background=surface,
            foreground="#f4f7fb",
            font=("Segoe UI Semibold", 12),
        )
        style.configure(
            "SearchLabel.TLabel",
            background=surface,
            foreground="#a5b2c2",
            font=("Segoe UI", 8),
        )
        style.configure(
            "Search.TEntry",
            fieldbackground=field,
            foreground="#ffffff",
            insertcolor="#ffffff",
            bordercolor=border,
            lightcolor=border,
            darkcolor=border,
            padding=(9, 6),
        )

        style.configure(
            "Enterprise.Treeview",
            background="#0d141c",
            fieldbackground="#0d141c",
            foreground="#e2e8f0",
            borderwidth=0,
            rowheight=37,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Enterprise.Treeview.Heading",
            background="#17202b",
            foreground="#b6c2d0",
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
        style.map("Enterprise.Treeview.Heading", background=[("active", "#1d2a38")])

        style.configure("Enterprise.TNotebook", background=inspector, borderwidth=0)
        style.configure(
            "Enterprise.TNotebook.Tab",
            background="#121b25",
            foreground="#aebbc9",
            borderwidth=0,
            padding=(16, 10),
            font=("Segoe UI Semibold", 9),
        )
        style.map(
            "Enterprise.TNotebook.Tab",
            background=[("selected", inspector), ("active", hover)],
            foreground=[("selected", "#ffffff"), ("active", "#ffffff")],
        )

        style.configure(
            "InspectorTitle.TLabel",
            background=inspector,
            foreground="#ffffff",
            font=("Segoe UI Semibold", 11),
        )
        style.configure(
            "InspectorKey.TLabel",
            background=inspector,
            foreground="#9eacbd",
            font=("Segoe UI Semibold", 8),
        )
        style.configure(
            "InspectorValue.TLabel",
            background=inspector,
            foreground="#f0f4f8",
            font=("Segoe UI", 9),
        )
        style.configure(
            "InspectorNote.TLabel",
            background=inspector,
            foreground="#7f90a4",
            font=("Segoe UI", 8),
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
            foreground=[("disabled", "#718096")],
        )
        style.configure(
            "Inspector.TButton",
            background="#17212d",
            foreground="#eef3f8",
            bordercolor=border,
            padding=(10, 7),
            font=("Segoe UI", 9),
        )
        style.map(
            "Inspector.TButton",
            background=[("active", hover), ("pressed", hover)],
            foreground=[("disabled", "#718096")],
        )
        style.configure(
            "Compact.TButton",
            background="#17212d",
            foreground="#dce5ef",
            bordercolor=border,
            padding=(8, 5),
            font=("Segoe UI", 8),
        )
        style.map(
            "Compact.TButton",
            background=[("active", hover), ("pressed", hover)],
            foreground=[("disabled", "#718096")],
        )

        style.configure(
            "Accent.Horizontal.TProgressbar",
            troughcolor="#0d141c",
            background=accent,
            bordercolor="#0d141c",
            lightcolor=accent,
            darkcolor=accent,
        )
        style.configure("TSeparator", background=border_soft)

        for menu in (self.language_menu, self.interface_menu, self.context_menu):
            menu.configure(
                background="#17212d",
                foreground="#f0f4f8",
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
