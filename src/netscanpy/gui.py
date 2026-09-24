from __future__ import annotations

import locale
import platform
import socket
import subprocess
import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, simpledialog, ttk

from .labels import get_label, load_labels, remove_label, set_label
from .network import detect_local_network, parse_network
from .scanner import Device, scan_network


TRANSLATIONS = {
    "fr": {
        "app_subtitle": "Scanner réseau local",
        "network": "Réseau",
        "scan": "Scanner",
        "ip": "Adresse IP",
        "mac": "Adresse MAC",
        "hostname": "Nom d'hôte",
        "label": "Étiquette",
        "language": "Langue",
        "interface": "Interface",
        "light": "Clair",
        "dark": "Sombre",
        "ready": "Prêt",
        "devices": "Appareils",
        "device": "appareil",
        "search": "Rechercher un appareil…",
        "status": "État",
        "current_network": "Réseau actuel",
        "ping": "Ping",
        "traceroute": "Traceroute",
        "scan_ports": "Scanner les ports courants",
        "open_browser": "Ouvrir dans le navigateur",
        "copy_ip": "Copier l'IP",
        "copy_mac": "Copier la MAC",
        "copy_hostname": "Copier le nom d'hôte",
        "details": "Afficher les détails",
        "set_label": "Définir une étiquette",
        "remove_label": "Supprimer l'étiquette",
        "copy": "Copier",
        "close": "Fermer",
        "summary": "Résumé",
        "terminal": "Sortie terminal",
        "waiting": "En attente des résultats…",
        "in_progress": "en cours…",
        "success": "réussi",
        "no_response": "aucune réponse",
        "error": "erreur",
        "open": "Ouvert",
        "closed": "Fermé",
        "service": "Service",
        "port": "Port",
        "unknown": "Inconnu",
        "none": "Aucune",
        "device_details": "Détails de l'appareil",
        "common_ports": "Ports courants",
        "scanning_ports": "Analyse des ports courants sur {ip}…",
        "scan_complete_ports": "Analyse terminée — {count} port(s) ouvert(s)",
        "label_for": "Étiquette pour {mac} :",
        "no_hostname": "Aucun nom d'hôte disponible pour cet appareil.",
        "scan_complete": "Analyse terminée",
        "scan_failed": "Échec de l'analyse",
        "scanning": "Analyse de {network}…",
        "copied": "{what} copié",
        "opening": "Ouverture de http://{ip}",
        "no_results": "Aucun appareil trouvé",
        "device_count": "{count} appareil(s)",
    },
    "en": {
        "app_subtitle": "Local network scanner",
        "network": "Network",
        "scan": "Scan",
        "ip": "IP address",
        "mac": "MAC address",
        "hostname": "Hostname",
        "label": "Label",
        "language": "Language",
        "interface": "Interface",
        "light": "Light",
        "dark": "Dark",
        "ready": "Ready",
        "devices": "Devices",
        "device": "device",
        "search": "Search devices…",
        "status": "Status",
        "current_network": "Current network",
        "ping": "Ping",
        "traceroute": "Traceroute",
        "scan_ports": "Scan common ports",
        "open_browser": "Open in browser",
        "copy_ip": "Copy IP",
        "copy_mac": "Copy MAC",
        "copy_hostname": "Copy hostname",
        "details": "Show details",
        "set_label": "Set label",
        "remove_label": "Remove label",
        "copy": "Copy",
        "close": "Close",
        "summary": "Summary",
        "terminal": "Terminal output",
        "waiting": "Waiting for results…",
        "in_progress": "in progress…",
        "success": "success",
        "no_response": "no response",
        "error": "error",
        "open": "Open",
        "closed": "Closed",
        "service": "Service",
        "port": "Port",
        "unknown": "Unknown",
        "none": "None",
        "device_details": "Device details",
        "common_ports": "Common ports",
        "scanning_ports": "Scanning common ports on {ip}…",
        "scan_complete_ports": "Scan complete — {count} open port(s)",
        "label_for": "Label for {mac}:",
        "no_hostname": "No hostname is available for this device.",
        "scan_complete": "Scan complete",
        "scan_failed": "Scan failed",
        "scanning": "Scanning {network}…",
        "copied": "{what} copied",
        "opening": "Opening http://{ip}",
        "no_results": "No devices found",
        "device_count": "{count} device(s)",
    },
    "de": {
        "app_subtitle": "Lokaler Netzwerkscanner",
        "network": "Netzwerk",
        "scan": "Scannen",
        "ip": "IP-Adresse",
        "mac": "MAC-Adresse",
        "hostname": "Hostname",
        "label": "Bezeichnung",
        "language": "Sprache",
        "interface": "Darstellung",
        "light": "Hell",
        "dark": "Dunkel",
        "ready": "Bereit",
        "devices": "Geräte",
        "device": "Gerät",
        "search": "Geräte suchen…",
        "status": "Status",
        "current_network": "Aktuelles Netzwerk",
        "ping": "Ping",
        "traceroute": "Traceroute",
        "scan_ports": "Häufige Ports scannen",
        "open_browser": "Im Browser öffnen",
        "copy_ip": "IP kopieren",
        "copy_mac": "MAC kopieren",
        "copy_hostname": "Hostname kopieren",
        "details": "Details anzeigen",
        "set_label": "Bezeichnung setzen",
        "remove_label": "Bezeichnung entfernen",
        "copy": "Kopieren",
        "close": "Schließen",
        "summary": "Zusammenfassung",
        "terminal": "Terminalausgabe",
        "waiting": "Warte auf Ergebnisse…",
        "in_progress": "läuft…",
        "success": "erfolgreich",
        "no_response": "keine Antwort",
        "error": "Fehler",
        "open": "Offen",
        "closed": "Geschlossen",
        "service": "Dienst",
        "port": "Port",
        "unknown": "Unbekannt",
        "none": "Keine",
        "device_details": "Gerätedetails",
        "common_ports": "Häufige Ports",
        "scanning_ports": "Häufige Ports auf {ip} werden gescannt…",
        "scan_complete_ports": "Scan beendet — {count} offene Port(s)",
        "label_for": "Bezeichnung für {mac}:",
        "no_hostname": "Für dieses Gerät ist kein Hostname verfügbar.",
        "scan_complete": "Scan abgeschlossen",
        "scan_failed": "Scan fehlgeschlagen",
        "scanning": "Scanne {network}…",
        "copied": "{what} kopiert",
        "opening": "Öffne http://{ip}",
        "no_results": "Keine Geräte gefunden",
        "device_count": "{count} Gerät(e)",
    },
    "zh": {
        "app_subtitle": "本地网络扫描器",
        "network": "网络",
        "scan": "扫描",
        "ip": "IP 地址",
        "mac": "MAC 地址",
        "hostname": "主机名",
        "label": "标签",
        "language": "语言",
        "interface": "界面",
        "light": "浅色",
        "dark": "深色",
        "ready": "就绪",
        "devices": "设备",
        "device": "设备",
        "search": "搜索设备…",
        "status": "状态",
        "current_network": "当前网络",
        "ping": "Ping",
        "traceroute": "路由跟踪",
        "scan_ports": "扫描常用端口",
        "open_browser": "在浏览器中打开",
        "copy_ip": "复制 IP",
        "copy_mac": "复制 MAC",
        "copy_hostname": "复制主机名",
        "details": "显示详细信息",
        "set_label": "设置标签",
        "remove_label": "删除标签",
        "copy": "复制",
        "close": "关闭",
        "summary": "摘要",
        "terminal": "终端输出",
        "waiting": "等待结果…",
        "in_progress": "进行中…",
        "success": "成功",
        "no_response": "无响应",
        "error": "错误",
        "open": "开放",
        "closed": "关闭",
        "service": "服务",
        "port": "端口",
        "unknown": "未知",
        "none": "无",
        "device_details": "设备详情",
        "common_ports": "常用端口",
        "scanning_ports": "正在扫描 {ip} 的常用端口…",
        "scan_complete_ports": "扫描完成 — 找到 {count} 个开放端口",
        "label_for": "{mac} 的标签：",
        "no_hostname": "此设备没有可用的主机名。",
        "scan_complete": "扫描完成",
        "scan_failed": "扫描失败",
        "scanning": "正在扫描 {network}…",
        "copied": "已复制{what}",
        "opening": "正在打开 http://{ip}",
        "no_results": "未找到设备",
        "device_count": "{count} 台设备",
    },
}


class NetScanPyApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("NetScanPy")
        self.geometry("1040x680")
        self.minsize(820, 560)

        self.language = "fr"
        self.theme = "dark"
        self.network_var = tk.StringVar()
        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value=self._t("ready"))
        self.count_var = tk.StringVar(value=self._t("device_count", count=0))
        self.network_stat_var = tk.StringVar(value="—")
        self.device_labels = load_labels()
        self.devices: list[Device] = []

        self._build_ui()
        self._build_menus()
        self._apply_theme()
        self._apply_language()
        self._load_default_network()
        self.search_var.trace_add("write", lambda *_: self._refresh_device_table())

    def _t(self, key: str, **kwargs: object) -> str:
        text = TRANSLATIONS.get(self.language, TRANSLATIONS["en"]).get(key, key)
        return text.format(**kwargs)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        self.header = ttk.Frame(self, style="Header.TFrame", padding=(24, 18))
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.columnconfigure(0, weight=1)

        brand = ttk.Frame(self.header, style="Header.TFrame")
        brand.grid(row=0, column=0, sticky="w")

        self.brand_title = ttk.Label(
            brand, text="NetScanPy", style="Brand.TLabel"
        )
        self.brand_title.pack(anchor="w")
        self.brand_subtitle = ttk.Label(
            brand, text=self._t("app_subtitle"), style="Subtitle.TLabel"
        )
        self.brand_subtitle.pack(anchor="w", pady=(2, 0))

        self.header_actions = ttk.Frame(self.header, style="Header.TFrame")
        self.header_actions.grid(row=0, column=1, sticky="e")

        self.scan_card = ttk.Frame(self, style="Card.TFrame", padding=(20, 18))
        self.scan_card.grid(row=1, column=0, sticky="ew", padx=24, pady=(18, 10))
        self.scan_card.columnconfigure(1, weight=1)

        self.network_label = ttk.Label(
            self.scan_card, text=self._t("network"), style="FieldLabel.TLabel"
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
        self.scan_button.grid(row=0, column=2, padx=(12, 0), ipadx=12, ipady=4)

        self.stats = ttk.Frame(self, style="Root.TFrame")
        self.stats.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 10))
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

        self.content_card = ttk.Frame(self, style="Card.TFrame", padding=(18, 16))
        self.content_card.grid(
            row=3, column=0, sticky="nsew", padx=24, pady=(0, 18)
        )
        self.content_card.columnconfigure(0, weight=1)
        self.content_card.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(self.content_card, style="Card.TFrame")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        toolbar.columnconfigure(0, weight=1)

        self.search_entry = ttk.Entry(
            toolbar,
            textvariable=self.search_var,
            style="Search.TEntry",
            font=("Segoe UI", 10),
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", ipady=5)

        table_wrap = ttk.Frame(self.content_card, style="Card.TFrame")
        table_wrap.grid(row=1, column=0, sticky="nsew")
        table_wrap.columnconfigure(0, weight=1)
        table_wrap.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            table_wrap,
            columns=("ip", "mac", "hostname", "label"),
            show="headings",
            selectmode="browse",
            style="Modern.Treeview",
        )
        self.tree.heading("ip", text=self._t("ip"))
        self.tree.heading("mac", text=self._t("mac"))
        self.tree.heading("hostname", text=self._t("hostname"))
        self.tree.heading("label", text=self._t("label"))
        self.tree.column("ip", width=150, minwidth=120, anchor="w")
        self.tree.column("mac", width=190, minwidth=160, anchor="w")
        self.tree.column("hostname", width=280, minwidth=170, anchor="w")
        self.tree.column("label", width=190, minwidth=120, anchor="w")

        scrollbar = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.progress = ttk.Progressbar(
            self.content_card, mode="indeterminate", style="Accent.Horizontal.TProgressbar"
        )
        self.progress.grid(row=2, column=0, sticky="ew", pady=(12, 0))

        self.context_menu = tk.Menu(self, tearoff=False)
        self._populate_context_menu()
        self.tree.bind("<ButtonRelease-3>", self._show_context_menu)
        self.tree.bind("<Shift-F10>", self._show_context_menu_keyboard)
        self.tree.bind("<Double-1>", lambda _e: self.show_details_selected())

    def _make_stat_card(
        self,
        parent: ttk.Frame,
        column: int,
        title: str,
        value_var: tk.StringVar,
    ) -> ttk.Frame:
        card = ttk.Frame(parent, style="Card.TFrame", padding=(18, 14))
        card.grid(
            row=0,
            column=column,
            sticky="nsew",
            padx=(0 if column == 0 else 6, 0 if column == 2 else 6),
        )
        title_label = ttk.Label(card, text=title, style="StatTitle.TLabel")
        title_label.pack(anchor="w")
        value_label = ttk.Label(
            card, textvariable=value_var, style="StatValue.TLabel"
        )
        value_label.pack(anchor="w", pady=(5, 0))
        card._title_label = title_label  # type: ignore[attr-defined]
        return card

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

        self.theme_choice = tk.StringVar(value=self.theme)
        self.interface_menu.add_radiobutton(
            label=self._t("light"),
            variable=self.theme_choice,
            value="light",
            command=lambda: self._set_theme("light"),
        )
        self.interface_menu.add_radiobutton(
            label=self._t("dark"),
            variable=self.theme_choice,
            value="dark",
            command=lambda: self._set_theme("dark"),
        )

        self.language_button = ttk.Menubutton(
            self.header_actions,
            text=self._t("language"),
            menu=self.language_menu,
            style="Header.TMenubutton",
        )
        self.language_button.pack(side="left", padx=(0, 8))

        self.interface_button = ttk.Menubutton(
            self.header_actions,
            text=self._t("interface"),
            menu=self.interface_menu,
            style="Header.TMenubutton",
        )
        self.interface_button.pack(side="left")

    def _populate_context_menu(self) -> None:
        self.context_menu.delete(0, "end")
        self.context_menu.add_command(label=self._t("ping"), command=self.ping_selected)
        self.context_menu.add_command(
            label=self._t("traceroute"), command=self.traceroute_selected
        )
        self.context_menu.add_command(
            label=self._t("scan_ports"), command=self.scan_common_ports_selected
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label=self._t("open_browser"), command=self.open_in_browser_selected
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label=self._t("copy_ip"), command=self.copy_ip_selected
        )
        self.context_menu.add_command(
            label=self._t("copy_mac"), command=self.copy_mac_selected
        )
        self.context_menu.add_command(
            label=self._t("copy_hostname"), command=self.copy_hostname_selected
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label=self._t("details"), command=self.show_details_selected
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label=self._t("set_label"), command=self.set_label_selected
        )
        self.context_menu.add_command(
            label=self._t("remove_label"), command=self.remove_label_selected
        )

    def _set_language(self, language: str) -> None:
        if language not in TRANSLATIONS:
            return
        self.language = language
        self.language_choice.set(language)
        self._apply_language()

    def _set_theme(self, theme: str) -> None:
        if theme not in ("light", "dark"):
            return
        self.theme = theme
        self.theme_choice.set(theme)
        self._apply_theme()

    def _apply_language(self) -> None:
        self.brand_subtitle.configure(text=self._t("app_subtitle"))
        self.network_label.configure(text=self._t("network"))
        self.scan_button.configure(text=self._t("scan"))
        self.language_button.configure(text=self._t("language"))
        self.interface_button.configure(text=self._t("interface"))
        self.interface_menu.entryconfigure(0, label=self._t("light"))
        self.interface_menu.entryconfigure(1, label=self._t("dark"))

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

    def _apply_theme(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        if self.theme == "dark":
            root = "#0f1115"
            header = "#151922"
            card = "#181d27"
            field = "#11151d"
            border = "#2b3342"
            fg = "#f5f7fb"
            muted = "#9aa6b6"
            accent = "#5b8cff"
            accent_hover = "#78a0ff"
            selected = "#24395f"
        else:
            root = "#eef2f7"
            header = "#ffffff"
            card = "#ffffff"
            field = "#f8fafc"
            border = "#dbe2ea"
            fg = "#152033"
            muted = "#667085"
            accent = "#356df3"
            accent_hover = "#285bd1"
            selected = "#dce8ff"

        self.configure(bg=root)
        style.configure("Root.TFrame", background=root)
        style.configure("Header.TFrame", background=header)
        style.configure("Card.TFrame", background=card)
        style.configure("TFrame", background=card)
        style.configure("TLabel", background=card, foreground=fg)
        style.configure(
            "Brand.TLabel",
            background=header,
            foreground=fg,
            font=("Segoe UI Semibold", 18),
        )
        style.configure(
            "Subtitle.TLabel",
            background=header,
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
            "StatTitle.TLabel",
            background=card,
            foreground=muted,
            font=("Segoe UI Semibold", 9),
        )
        style.configure(
            "StatValue.TLabel",
            background=card,
            foreground=fg,
            font=("Segoe UI Semibold", 12),
        )
        style.configure(
            "Modern.TEntry",
            fieldbackground=field,
            foreground=fg,
            insertcolor=fg,
            bordercolor=border,
            lightcolor=border,
            darkcolor=border,
            padding=(10, 8),
        )
        style.configure(
            "Search.TEntry",
            fieldbackground=field,
            foreground=fg,
            insertcolor=fg,
            bordercolor=border,
            lightcolor=border,
            darkcolor=border,
            padding=(10, 8),
        )
        style.configure(
            "Accent.TButton",
            background=accent,
            foreground="#ffffff",
            bordercolor=accent,
            padding=(14, 8),
            font=("Segoe UI Semibold", 10),
        )
        style.map(
            "Accent.TButton",
            background=[("active", accent_hover), ("pressed", accent_hover)],
            foreground=[("disabled", "#c7cfdb")],
        )
        style.configure(
            "Header.TMenubutton",
            background=header,
            foreground=fg,
            bordercolor=border,
            padding=(12, 7),
            font=("Segoe UI", 9),
        )
        style.map(
            "Header.TMenubutton",
            background=[("active", card), ("pressed", card)],
        )
        style.configure(
            "Modern.Treeview",
            background=field,
            fieldbackground=field,
            foreground=fg,
            bordercolor=border,
            rowheight=34,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Modern.Treeview.Heading",
            background=card,
            foreground=muted,
            bordercolor=border,
            padding=(8, 9),
            font=("Segoe UI Semibold", 9),
        )
        style.map(
            "Modern.Treeview",
            background=[("selected", selected)],
            foreground=[("selected", fg)],
        )
        style.configure(
            "Accent.Horizontal.TProgressbar",
            troughcolor=field,
            background=accent,
            bordercolor=field,
            lightcolor=accent,
            darkcolor=accent,
        )

        menu_bg = card
        menu_fg = fg
        for menu in (self.language_menu, self.interface_menu, self.context_menu):
            menu.configure(
                background=menu_bg,
                foreground=menu_fg,
                activebackground=selected,
                activeforeground=fg,
                selectcolor=accent,
                borderwidth=0,
            )

        self._apply_windows_titlebar_theme()

    def _apply_windows_titlebar_theme(self) -> None:
        if platform.system() != "Windows":
            return
        try:
            import ctypes

            self.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            enabled = ctypes.c_int(1 if self.theme == "dark" else 0)
            for attribute in (20, 19):
                result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    attribute,
                    ctypes.byref(enabled),
                    ctypes.sizeof(enabled),
                )
                if result == 0:
                    break
            self.after(20, self._force_windows_frame_refresh)
        except Exception:
            pass

    def _force_windows_frame_refresh(self) -> None:
        if platform.system() != "Windows":
            return
        try:
            width, height = self.winfo_width(), self.winfo_height()
            x, y = self.winfo_x(), self.winfo_y()
            if width > 1 and height > 1:
                self.geometry(f"{width + 1}x{height}+{x}+{y}")
                self.update_idletasks()
                self.geometry(f"{width}x{height}+{x}+{y}")
        except tk.TclError:
            pass

    def _load_default_network(self) -> None:
        try:
            network = str(detect_local_network())
            self.network_var.set(network)
            self.network_stat_var.set(network)
        except RuntimeError as exc:
            self.network_var.set("")
            self.network_stat_var.set("—")
            self.status_var.set(str(exc))

    def _show_context_menu(self, event: tk.Event) -> str:
        item = self.tree.identify_row(event.y)
        if not item:
            return "break"
        self.tree.selection_set(item)
        self.tree.focus(item)
        self.context_menu.post(event.x_root, event.y_root)
        return "break"

    def _show_context_menu_keyboard(self, _event: tk.Event) -> str:
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

        bbox = self.tree.bbox(item)
        if not bbox:
            return "break"
        x, y, width, height = bbox
        self.context_menu.post(
            self.tree.winfo_rootx() + x + min(width // 2, 80),
            self.tree.winfo_rooty() + y + height,
        )
        return "break"

    def _selected_device_values(self) -> tuple[str, str, str, str] | None:
        selected = self.tree.selection()
        if not selected:
            return None
        values = self.tree.item(selected[0], "values")
        if len(values) < 4:
            return None
        return tuple(str(value) for value in values[:4])  # type: ignore[return-value]

    def _copy_to_clipboard(self, value: str, description: str) -> None:
        if not value:
            return
        self.clipboard_clear()
        self.clipboard_append(value)
        self.status_var.set(self._t("copied", what=description))

    def copy_ip_selected(self) -> None:
        values = self._selected_device_values()
        if values:
            self._copy_to_clipboard(values[0], self._t("ip"))

    def copy_mac_selected(self) -> None:
        values = self._selected_device_values()
        if values:
            self._copy_to_clipboard(values[1], self._t("mac"))

    def copy_hostname_selected(self) -> None:
        values = self._selected_device_values()
        if not values:
            return
        hostname = values[2]
        if not hostname or hostname == "Unknown":
            messagebox.showinfo("NetScanPy", self._t("no_hostname"))
            return
        self._copy_to_clipboard(hostname, self._t("hostname"))

    def open_in_browser_selected(self) -> None:
        values = self._selected_device_values()
        if not values:
            return
        ip = values[0]
        webbrowser.open(f"http://{ip}")
        self.status_var.set(self._t("opening", ip=ip))

    def show_details_selected(self) -> None:
        values = self._selected_device_values()
        if not values:
            return

        ip, mac, hostname, label = values
        window = tk.Toplevel(self)
        window.title(f"{self._t('device_details')} — {ip}")
        window.geometry("480x310")
        window.resizable(False, False)
        window.transient(self)

        frame = ttk.Frame(window, style="Card.TFrame", padding=22)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame, text=self._t("device_details"), style="Brand.TLabel"
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))

        details = (
            (self._t("ip"), ip),
            (self._t("mac"), mac),
            (self._t("hostname"), hostname or self._t("unknown")),
            (self._t("label"), label or self._t("none")),
        )
        for row, (name, value) in enumerate(details, start=1):
            ttk.Label(frame, text=name, style="FieldLabel.TLabel").grid(
                row=row, column=0, sticky="w", pady=7, padx=(0, 18)
            )
            ttk.Label(frame, text=value).grid(row=row, column=1, sticky="w", pady=7)

        ttk.Button(frame, text=self._t("close"), command=window.destroy).grid(
            row=len(details) + 1, column=1, sticky="e", pady=(18, 0)
        )
        self._apply_windows_titlebar_theme()

    def set_label_selected(self) -> None:
        values = self._selected_device_values()
        if not values:
            return
        _, mac, _, current_label = values
        label = simpledialog.askstring(
            "NetScanPy",
            self._t("label_for", mac=mac),
            initialvalue=current_label,
            parent=self,
        )
        if label is None:
            return
        label = label.strip()
        if label:
            set_label(mac, label)
            self.device_labels[mac.lower()] = label
        else:
            remove_label(mac)
            self.device_labels.pop(mac.lower(), None)
        self._refresh_device_table()

    def remove_label_selected(self) -> None:
        values = self._selected_device_values()
        if not values:
            return
        remove_label(values[1])
        self.device_labels.pop(values[1].lower(), None)
        self._refresh_device_table()

    def ping_selected(self) -> None:
        values = self._selected_device_values()
        if not values:
            return
        ip = values[0]
        self.status_var.set(f"Ping {ip}…")
        ping_window = self._create_ping_window(ip)
        threading.Thread(
            target=self._ping_worker, args=(ip, ping_window), daemon=True
        ).start()

    def _windows_oem_encoding(self) -> str:
        try:
            import ctypes
            return f"cp{ctypes.windll.kernel32.GetOEMCP()}"
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
                self.after(0, self._append_ping_output, ping_window, line)

            return_code = process.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
            self.after(0, self._ping_failed_window, ip, ping_window, str(exc))
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
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        return [line for line in lines if any(key in line for key in keywords)][-8:]

    def _create_ping_window(self, ip: str) -> dict[str, object]:
        window = tk.Toplevel(self)
        window.title(f"Ping {ip}")
        window.geometry("780x520")
        window.minsize(620, 400)
        window.transient(self)

        container = ttk.Frame(window, style="Card.TFrame", padding=18)
        container.pack(fill="both", expand=True)

        title_label = ttk.Label(
            container,
            text=f"Ping {ip} — {self._t('in_progress')}",
            style="Brand.TLabel",
        )
        title_label.pack(anchor="w")

        summary_frame = ttk.LabelFrame(
            container, text=self._t("summary"), padding=12
        )
        summary_frame.pack(fill="x", pady=(14, 12))
        summary_label = ttk.Label(
            summary_frame, text=self._t("waiting"), justify="left"
        )
        summary_label.pack(anchor="w")

        terminal_frame = ttk.LabelFrame(
            container, text=self._t("terminal"), padding=8
        )
        terminal_frame.pack(fill="both", expand=True)

        terminal_bg = "#0b0e14" if self.theme == "dark" else "#161b22"
        text_widget = tk.Text(
            terminal_frame,
            wrap="word",
            font=("Consolas", 10),
            bg=terminal_bg,
            fg="#e6edf3",
            insertbackground="#e6edf3",
            relief="flat",
            padx=10,
            pady=10,
        )
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(
            terminal_frame, orient="vertical", command=text_widget.yview
        )
        scrollbar.pack(side="right", fill="y")
        text_widget.configure(yscrollcommand=scrollbar.set, state="disabled")

        buttons = ttk.Frame(container, style="Card.TFrame")
        buttons.pack(fill="x", pady=(12, 0))

        def copy_output() -> None:
            text_widget.configure(state="normal")
            output = text_widget.get("1.0", "end-1c")
            text_widget.configure(state="disabled")
            window.clipboard_clear()
            window.clipboard_append(output)

        ttk.Button(buttons, text=self._t("copy"), command=copy_output).pack(side="left")
        ttk.Button(buttons, text=self._t("close"), command=window.destroy).pack(side="right")

        self._apply_windows_titlebar_theme()
        return {
            "window": window,
            "title_label": title_label,
            "summary_label": summary_label,
            "text_widget": text_widget,
        }

    def _append_ping_output(
        self, ping_window: dict[str, object], text: str
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

        summary = self._extract_ping_summary(text_widget.get("1.0", "end-1c"))
        summary_label = ping_window["summary_label"]
        if isinstance(summary_label, ttk.Label) and summary:
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

        self.status_var.set(
            f"{ip} — {self._t('success' if success else 'no_response')}"
        )
        if isinstance(title_label, ttk.Label):
            title_label.configure(
                text=f"Ping {ip} — {self._t('success' if success else 'no_response')}"
            )
        summary = self._extract_ping_summary(output)
        if isinstance(summary_label, ttk.Label):
            summary_label.configure(
                text="\n".join(summary) if summary else self._t("no_response")
            )

    def _ping_failed_window(
        self, ip: str, ping_window: dict[str, object], error: str
    ) -> None:
        self.status_var.set(f"Ping {ip} — {self._t('error')}")
        title_label = ping_window.get("title_label")
        summary_label = ping_window.get("summary_label")
        if isinstance(title_label, ttk.Label):
            title_label.configure(text=f"Ping {ip} — {self._t('error')}")
        if isinstance(summary_label, ttk.Label):
            summary_label.configure(text=error)
        self._append_ping_output(ping_window, f"\nError: {error}\n")

    def traceroute_selected(self) -> None:
        values = self._selected_device_values()
        if not values:
            return
        ip = values[0]
        system = platform.system()
        if system == "Windows":
            command = ["tracert", "-d", "-w", "1000", ip]
            encoding = self._windows_oem_encoding()
            creationflags = subprocess.CREATE_NO_WINDOW
        else:
            command = ["traceroute", "-n", "-w", "1", ip]
            encoding = locale.getpreferredencoding(False) or "utf-8"
            creationflags = 0
        self._start_live_command(
            f"Traceroute {ip}", command, encoding, creationflags
        )

    def _start_live_command(
        self,
        title: str,
        command: list[str],
        encoding: str,
        creationflags: int = 0,
    ) -> None:
        window = tk.Toplevel(self)
        window.title(title)
        window.geometry("780x500")
        window.transient(self)

        container = ttk.Frame(window, style="Card.TFrame", padding=18)
        container.pack(fill="both", expand=True)

        title_label = ttk.Label(
            container,
            text=f"{title} — {self._t('in_progress')}",
            style="Brand.TLabel",
        )
        title_label.pack(anchor="w")

        terminal_frame = ttk.LabelFrame(
            container, text=self._t("terminal"), padding=8
        )
        terminal_frame.pack(fill="both", expand=True, pady=(14, 0))
        text_widget = tk.Text(
            terminal_frame,
            wrap="word",
            font=("Consolas", 10),
            bg="#0b0e14",
            fg="#e6edf3",
            insertbackground="#e6edf3",
            relief="flat",
            padx=10,
            pady=10,
        )
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(
            terminal_frame, orient="vertical", command=text_widget.yview
        )
        scrollbar.pack(side="right", fill="y")
        text_widget.configure(yscrollcommand=scrollbar.set, state="disabled")

        def append_line(line: str) -> None:
            if not window.winfo_exists():
                return
            text_widget.configure(state="normal")
            text_widget.insert("end", line)
            text_widget.see("end")
            text_widget.configure(state="disabled")

        def finish(return_code: int) -> None:
            if window.winfo_exists():
                title_label.configure(
                    text=f"{title} — {'OK' if return_code == 0 else self._t('error')}"
                )

        def worker() -> None:
            try:
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    creationflags=creationflags,
                )
                if process.stdout is None:
                    raise RuntimeError("Unable to read command output.")
                while True:
                    raw = process.stdout.readline()
                    if not raw:
                        break
                    self.after(0, append_line, raw.decode(encoding, errors="replace"))
                self.after(0, finish, process.wait())
            except Exception as exc:
                self.after(0, append_line, f"\nError: {exc}\n")
                self.after(0, finish, 1)

        buttons = ttk.Frame(container, style="Card.TFrame")
        buttons.pack(fill="x", pady=(12, 0))

        def copy_output() -> None:
            text_widget.configure(state="normal")
            output = text_widget.get("1.0", "end-1c")
            text_widget.configure(state="disabled")
            window.clipboard_clear()
            window.clipboard_append(output)

        ttk.Button(buttons, text=self._t("copy"), command=copy_output).pack(side="left")
        ttk.Button(buttons, text=self._t("close"), command=window.destroy).pack(side="right")
        threading.Thread(target=worker, daemon=True).start()
        self._apply_windows_titlebar_theme()

    def _insert_port_result(
        self, tree: ttk.Treeview, port: int, service: str, status: str
    ) -> None:
        if tree.winfo_exists():
            tree.insert("", "end", values=(port, service, status))

    def scan_common_ports_selected(self) -> None:
        values = self._selected_device_values()
        if not values:
            return
        ip = values[0]
        ports = {
            21: "FTP",
            22: "SSH",
            23: "Telnet",
            25: "SMTP",
            53: "DNS",
            80: "HTTP",
            110: "POP3",
            139: "NetBIOS",
            143: "IMAP",
            443: "HTTPS",
            445: "SMB",
            3389: "RDP",
            5900: "VNC",
            8080: "HTTP-alt",
            8443: "HTTPS-alt",
        }

        window = tk.Toplevel(self)
        window.title(f"{self._t('common_ports')} — {ip}")
        window.geometry("560x470")
        window.transient(self)

        frame = ttk.Frame(window, style="Card.TFrame", padding=18)
        frame.pack(fill="both", expand=True)
        status = ttk.Label(
            frame,
            text=self._t("scanning_ports", ip=ip),
            style="StatValue.TLabel",
        )
        status.pack(anchor="w", pady=(0, 12))

        tree = ttk.Treeview(
            frame,
            columns=("port", "service", "status"),
            show="headings",
            style="Modern.Treeview",
        )
        tree.heading("port", text=self._t("port"))
        tree.heading("service", text=self._t("service"))
        tree.heading("status", text=self._t("status"))
        tree.column("port", width=100, anchor="center")
        tree.column("service", width=220)
        tree.column("status", width=140, anchor="center")
        tree.pack(fill="both", expand=True)

        def worker() -> None:
            open_count = 0
            for port, service in ports.items():
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.35)
                try:
                    is_open = sock.connect_ex((ip, port)) == 0
                except OSError:
                    is_open = False
                finally:
                    sock.close()

                if is_open:
                    open_count += 1
                self.after(
                    0,
                    self._insert_port_result,
                    tree,
                    port,
                    service,
                    self._t("open") if is_open else self._t("closed"),
                )

            self.after(
                0,
                status.configure,
                {"text": self._t("scan_complete_ports", count=open_count)},
            )

        threading.Thread(target=worker, daemon=True).start()
        self._apply_windows_titlebar_theme()

    def start_scan(self) -> None:
        if self.scan_button.instate(["disabled"]):
            return

        try:
            network = parse_network(self.network_var.get().strip())
        except ValueError as exc:
            messagebox.showerror("NetScanPy", str(exc))
            return

        self.devices.clear()
        self._refresh_device_table()
        self.network_stat_var.set(str(network))
        self.status_var.set(self._t("scanning", network=network))
        self.count_var.set(self._t("device_count", count=0))
        self.scan_button.state(["disabled"])
        self.network_entry.state(["disabled"])
        self.progress.start(10)

        threading.Thread(
            target=self._scan_worker, args=(str(network),), daemon=True
        ).start()

    def _scan_worker(self, network: str) -> None:
        try:
            devices = scan_network(network, timeout=1.0)
        except Exception as exc:
            self.after(0, self._scan_failed, str(exc))
            return
        self.after(0, self._scan_finished, devices)

    def _scan_finished(self, devices: list[Device]) -> None:
        self.devices = devices
        self._refresh_device_table()
        self.count_var.set(self._t("device_count", count=len(devices)))
        self.status_var.set(self._t("scan_complete"))
        self._set_idle_state()

    def _scan_failed(self, error: str) -> None:
        self.status_var.set(self._t("scan_failed"))
        self._set_idle_state()
        messagebox.showerror("NetScanPy", error)

    def _refresh_device_table(self) -> None:
        selected_mac = None
        selected = self.tree.selection()
        if selected:
            values = self.tree.item(selected[0], "values")
            if len(values) >= 2:
                selected_mac = str(values[1]).lower()

        for item in self.tree.get_children():
            self.tree.delete(item)

        query = self.search_var.get().strip().lower()
        for device in self.devices:
            label = get_label(device.mac, self.device_labels)
            haystack = " ".join(
                (device.ip, device.mac, device.hostname or "", label)
            ).lower()
            if query and query not in haystack:
                continue

            item = self.tree.insert(
                "",
                "end",
                values=(device.ip, device.mac, device.hostname, label),
            )
            if selected_mac and device.mac.lower() == selected_mac:
                self.tree.selection_set(item)

    def _set_idle_state(self) -> None:
        self.progress.stop()
        self.scan_button.state(["!disabled"])
        self.network_entry.state(["!disabled"])


def main() -> None:
    app = NetScanPyApp()
    app.mainloop()


if __name__ == "__main__":
    main()
