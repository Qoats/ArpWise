from __future__ import annotations

import ipaddress
import socket
import subprocess
import sys
import threading
import webbrowser
from dataclasses import dataclass

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .labels import get_label, load_labels
from .network_info import PublicNetworkInfo, fetch_public_network_info, get_local_network_info
from .scanner import Device, scan_network


APP_STYLE = """
QWidget {
    background: #0b0f14;
    color: #e8eef6;
    font-family: "Segoe UI";
    font-size: 13px;
}
QMainWindow, #root { background: #0b0f14; }
#topbar {
    background: #0d1219;
    border-bottom: 1px solid #202a36;
}
#brand { font-size: 21px; font-weight: 700; color: #ffffff; }
#muted { color: #8f9dad; }
#sectionTitle { font-size: 15px; font-weight: 650; color: #f6f9fc; }
#panel {
    background: #111821;
    border: 1px solid #202a36;
    border-radius: 8px;
}
#inspector {
    background: #0f161f;
    border: 1px solid #202a36;
    border-radius: 8px;
}
QLineEdit {
    min-height: 38px;
    padding: 0 12px;
    background: #0b1118;
    color: #ffffff;
    border: 1px solid #2b3746;
    border-radius: 6px;
    selection-background-color: #245d9b;
}
QLineEdit:focus { border: 1px solid #3b82f6; }
QPushButton {
    min-height: 38px;
    padding: 0 14px;
    background: #17212d;
    color: #edf3f9;
    border: 1px solid #2b3746;
    border-radius: 6px;
}
QPushButton:hover { background: #1d2a38; border-color: #3a4b60; }
QPushButton:pressed { background: #111b26; }
QPushButton:disabled { color: #687789; background: #121922; }
QPushButton#primary {
    background: #2f7df4;
    color: white;
    border: 1px solid #2f7df4;
    font-weight: 650;
}
QPushButton#primary:hover { background: #458cf5; }
QTableWidget {
    background: #0d141c;
    alternate-background-color: #101923;
    color: #e3eaf2;
    border: 0;
    gridline-color: transparent;
    selection-background-color: #1f4e7f;
    selection-color: #ffffff;
    outline: 0;
}
QHeaderView::section {
    background: #151e29;
    color: #b7c3d1;
    padding: 10px 12px;
    border: 0;
    border-bottom: 1px solid #283442;
    font-weight: 600;
}
QTableWidget::item { padding: 8px 12px; border: 0; }
QTabWidget::pane {
    border: 0;
    background: #0f161f;
}
QTabBar::tab {
    background: #111a24;
    color: #9eacbd;
    border: 0;
    border-bottom: 2px solid transparent;
    padding: 11px 18px;
}
QTabBar::tab:selected {
    color: #ffffff;
    background: #0f161f;
    border-bottom: 2px solid #3b82f6;
}
QTabBar::tab:hover { color: #ffffff; background: #17212d; }
QTextEdit {
    background: #090d12;
    color: #e6edf3;
    border: 1px solid #263241;
    border-radius: 6px;
    font-family: Consolas;
    font-size: 12px;
}
"""


class WorkerSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)


class FunctionWorker(QRunnable):
    def __init__(self, fn, *args) -> None:
        super().__init__()
        self.fn = fn
        self.args = args
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            result = self.fn(*self.args)
        except Exception as exc:
            self.signals.failed.emit(str(exc))
        else:
            self.signals.finished.emit(result)


@dataclass
class SelectedDevice:
    ip: str
    mac: str
    hostname: str
    label: str


class NetScanQt(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("NetScanPy")
        self.resize(1320, 820)
        self.setMinimumSize(1080, 680)
        self.pool = QThreadPool.globalInstance()
        self.devices: list[Device] = []
        self.device_labels = load_labels()
        self.public_info: PublicNetworkInfo | None = None
        self.current_network = "—"
        self._build_ui()
        self._detect_network()
        self._refresh_network_info()
        self.start_scan()

    def _build_ui(self) -> None:
        root = QWidget(objectName="root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        topbar = QFrame(objectName="topbar")
        top = QHBoxLayout(topbar)
        top.setContentsMargins(24, 0, 24, 0)
        top.setSpacing(12)
        topbar.setFixedHeight(62)
        brand = QLabel("NetScanPy", objectName="brand")
        top.addWidget(brand)
        top.addStretch(1)
        lang = QPushButton("Français")
        lang.setFixedWidth(110)
        lang.setEnabled(False)
        top.addWidget(lang)
        outer.addWidget(topbar)

        command = QFrame(objectName="panel")
        command.setStyleSheet("QFrame#panel { border-radius: 0; border-left: 0; border-right: 0; }")
        cmd = QHBoxLayout(command)
        cmd.setContentsMargins(24, 14, 24, 14)
        cmd.setSpacing(12)
        label = QLabel("Réseau")
        label.setObjectName("muted")
        self.network_edit = QLineEdit()
        self.network_edit.setPlaceholderText("Détection automatique…")
        self.scan_button = QPushButton("Scanner", objectName="primary")
        self.scan_button.setFixedWidth(140)
        self.scan_button.clicked.connect(self.start_scan)
        cmd.addWidget(label)
        cmd.addWidget(self.network_edit, 1)
        cmd.addWidget(self.scan_button)
        outer.addWidget(command)

        self.status_line = QLabel("Prêt")
        self.status_line.setObjectName("muted")
        self.status_line.setContentsMargins(24, 8, 24, 8)
        self.status_line.setStyleSheet("background:#0d141c;border-bottom:1px solid #202a36;color:#9eacbd;")
        outer.addWidget(self.status_line)

        body = QWidget()
        layout = QHBoxLayout(body)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        left = QFrame(objectName="panel")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        header = QWidget()
        hh = QHBoxLayout(header)
        hh.setContentsMargins(18, 14, 18, 14)
        title = QLabel("Inventaire réseau", objectName="sectionTitle")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Rechercher IP, MAC, hôte…")
        self.search.setFixedWidth(280)
        self.search.textChanged.connect(self._render_devices)
        hh.addWidget(title)
        hh.addStretch(1)
        hh.addWidget(self.search)
        left_layout.addWidget(header)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Adresse IP", "Adresse MAC", "Nom d’hôte", "Étiquette"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        left_layout.addWidget(self.table, 1)

        self.tabs = QTabWidget(objectName="inspector")
        self.tabs.setFixedWidth(365)
        self.device_tab = QWidget()
        self.network_tab = QWidget()
        self.tabs.addTab(self.device_tab, "Appareil")
        self.tabs.addTab(self.network_tab, "Réseau")
        self._build_device_tab()
        self._build_network_tab()

        layout.addWidget(left, 1)
        layout.addWidget(self.tabs)
        outer.addWidget(body, 1)

    def _field(self, layout: QVBoxLayout, name: str) -> QLabel:
        key = QLabel(name, objectName="muted")
        value = QLabel("—")
        value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        value.setWordWrap(True)
        layout.addWidget(key)
        layout.addWidget(value)
        layout.addSpacing(10)
        return value

    def _build_device_tab(self) -> None:
        layout = QVBoxLayout(self.device_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        title = QLabel("Appareil", objectName="sectionTitle")
        layout.addWidget(title)
        layout.addSpacing(12)
        self.dev_ip = self._field(layout, "Adresse IP")
        self.dev_mac = self._field(layout, "Adresse MAC")
        self.dev_host = self._field(layout, "Nom d’hôte")
        self.dev_label = self._field(layout, "Étiquette")
        layout.addSpacing(4)
        actions = QLabel("Actions", objectName="muted")
        layout.addWidget(actions)
        self.ping_btn = QPushButton("Ping", objectName="primary")
        self.trace_btn = QPushButton("Traceroute")
        self.ports_btn = QPushButton("Scanner les ports courants")
        self.browser_btn = QPushButton("Ouvrir dans le navigateur")
        self.ping_btn.clicked.connect(lambda: self._run_command("Ping", self._ping_command()))
        self.trace_btn.clicked.connect(lambda: self._run_command("Traceroute", self._trace_command()))
        self.ports_btn.clicked.connect(self._scan_ports)
        self.browser_btn.clicked.connect(self._open_browser)
        for button in (self.ping_btn, self.trace_btn, self.ports_btn, self.browser_btn):
            button.setEnabled(False)
            layout.addWidget(button)
        layout.addStretch(1)

    def _build_network_tab(self) -> None:
        layout = QVBoxLayout(self.network_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        local_title = QLabel("Réseau local", objectName="sectionTitle")
        layout.addWidget(local_title)
        layout.addSpacing(10)
        self.net_iface = self._field(layout, "Interface")
        self.net_ip = self._field(layout, "IP locale")
        self.net_mask = self._field(layout, "Masque")
        self.net_subnet = self._field(layout, "Sous-réseau")
        public_title = QLabel("Connexion Internet", objectName="sectionTitle")
        layout.addWidget(public_title)
        layout.addSpacing(10)
        self.pub_ip = self._field(layout, "IP publique")
        self.pub_loc = self._field(layout, "Localisation")
        self.pub_coords = self._field(layout, "Latitude / longitude")
        self.pub_org = self._field(layout, "Opérateur / organisation")
        self.pub_asn = self._field(layout, "ASN")
        self.pub_tz = self._field(layout, "Fuseau horaire")
        buttons = QHBoxLayout()
        refresh = QPushButton("Actualiser")
        map_btn = QPushButton("Carte")
        refresh.clicked.connect(self._refresh_network_info)
        map_btn.clicked.connect(self._open_map)
        buttons.addWidget(refresh)
        buttons.addWidget(map_btn)
        layout.addLayout(buttons)
        note = QLabel("La géolocalisation IP est approximative et concerne l’IP publique.", objectName="muted")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)

    def _detect_network(self) -> str | None:
        local = get_local_network_info()
        if local is None:
            return None
        self.current_network = local.network
        self.network_edit.setText(local.network)
        self.net_iface.setText(local.interface)
        self.net_ip.setText(local.ip)
        self.net_mask.setText(local.netmask)
        self.net_subnet.setText(local.network)
        return local.network

    def start_scan(self) -> None:
        detected = self._detect_network()
        network = detected or self.network_edit.text().strip()
        if not network:
            QMessageBox.warning(self, "NetScanPy", "Aucun réseau local IPv4 n’a été détecté.")
            return
        try:
            ipaddress.ip_network(network, strict=False)
        except ValueError:
            QMessageBox.warning(self, "NetScanPy", "Réseau IPv4 invalide.")
            return
        self.scan_button.setEnabled(False)
        self.status_line.setText(f"Analyse de {network}…")
        worker = FunctionWorker(scan_network, network, 1.0)
        worker.signals.finished.connect(self._scan_finished)
        worker.signals.failed.connect(self._scan_failed)
        self.pool.start(worker)

    def _scan_finished(self, devices: object) -> None:
        self.devices = list(devices) if isinstance(devices, list) else []
        self._render_devices()
        self.status_line.setText(f"{len(self.devices)} appareil(s) détecté(s) · {self.current_network}")
        self.scan_button.setEnabled(True)

    def _scan_failed(self, error: str) -> None:
        self.scan_button.setEnabled(True)
        self.status_line.setText("Échec du scan")
        QMessageBox.critical(self, "NetScanPy", error)

    def _render_devices(self) -> None:
        query = self.search.text().strip().lower() if hasattr(self, "search") else ""
        rows: list[tuple[str, str, str, str]] = []
        for device in self.devices:
            label = get_label(device.mac, self.device_labels)
            values = (device.ip, device.mac, device.hostname or "Unknown", label)
            if query and query not in " ".join(values).lower():
                continue
            rows.append(values)
        self.table.setRowCount(len(rows))
        for row, values in enumerate(rows):
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
        if rows:
            self.table.selectRow(0)

    def _selected(self) -> SelectedDevice | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        values = [self.table.item(row, col).text() if self.table.item(row, col) else "" for col in range(4)]
        return SelectedDevice(*values)

    def _selection_changed(self) -> None:
        device = self._selected()
        enabled = device is not None
        for button in (self.ping_btn, self.trace_btn, self.ports_btn, self.browser_btn):
            button.setEnabled(enabled)
        if not device:
            for label in (self.dev_ip, self.dev_mac, self.dev_host, self.dev_label):
                label.setText("—")
            return
        self.dev_ip.setText(device.ip)
        self.dev_mac.setText(device.mac)
        self.dev_host.setText(device.hostname or "Unknown")
        self.dev_label.setText(device.label or "Aucune")

    def _refresh_network_info(self) -> None:
        self._detect_network()
        self.pub_ip.setText("Chargement…")
        worker = FunctionWorker(fetch_public_network_info)
        worker.signals.finished.connect(self._public_info_ready)
        worker.signals.failed.connect(self._public_info_failed)
        self.pool.start(worker)

    def _public_info_ready(self, result: object) -> None:
        if not isinstance(result, PublicNetworkInfo):
            return
        self.public_info = result
        self.pub_ip.setText(result.ip)
        location = ", ".join(part for part in (result.city, result.region, result.country) if part and part != "—") or "—"
        self.pub_loc.setText(location)
        self.pub_coords.setText(f"{result.latitude}, {result.longitude}")
        self.pub_org.setText(result.organization)
        self.pub_asn.setText(result.asn)
        tz = result.timezone if result.utc_offset == "—" else f"{result.timezone} ({result.utc_offset})"
        self.pub_tz.setText(tz)

    def _public_info_failed(self, _error: str) -> None:
        for label in (self.pub_ip, self.pub_loc, self.pub_coords, self.pub_org, self.pub_asn, self.pub_tz):
            label.setText("Indisponible")

    def _open_map(self) -> None:
        info = self.public_info
        if info and info.latitude != "—" and info.longitude != "—":
            webbrowser.open(f"https://www.openstreetmap.org/?mlat={info.latitude}&mlon={info.longitude}#map=12/{info.latitude}/{info.longitude}")

    def _open_browser(self) -> None:
        device = self._selected()
        if device:
            webbrowser.open(f"http://{device.ip}")

    def _ping_command(self) -> list[str]:
        device = self._selected()
        if not device:
            return []
        return ["ping", "-n" if sys.platform.startswith("win") else "-c", "4", device.ip]

    def _trace_command(self) -> list[str]:
        device = self._selected()
        if not device:
            return []
        if sys.platform.startswith("win"):
            return ["tracert", "-d", device.ip]
        return ["traceroute", "-n", device.ip]

    def _run_command(self, title: str, command: list[str]) -> None:
        if not command:
            return
        worker = FunctionWorker(self._execute_command, command)
        worker.signals.finished.connect(lambda output: self._show_output(title, str(output)))
        worker.signals.failed.connect(lambda error: QMessageBox.critical(self, title, error))
        self.pool.start(worker)

    @staticmethod
    def _execute_command(command: list[str]) -> str:
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
        completed = subprocess.run(command, capture_output=True, creationflags=creationflags, timeout=45)
        encoding = "cp850" if sys.platform.startswith("win") else "utf-8"
        return completed.stdout.decode(encoding, errors="replace") + completed.stderr.decode(encoding, errors="replace")

    def _show_output(self, title: str, output: str) -> None:
        dialog = QMessageBox(self)
        dialog.setWindowTitle(title)
        dialog.setText(title)
        dialog.setDetailedText(output or "Aucune sortie")
        dialog.exec()

    def _scan_ports(self) -> None:
        device = self._selected()
        if not device:
            return
        worker = FunctionWorker(self._port_scan, device.ip)
        worker.signals.finished.connect(lambda result: self._show_output("Ports courants", str(result)))
        worker.signals.failed.connect(lambda error: QMessageBox.critical(self, "Ports", error))
        self.pool.start(worker)

    @staticmethod
    def _port_scan(ip: str) -> str:
        ports = {21: "FTP", 22: "SSH", 23: "Telnet", 53: "DNS", 80: "HTTP", 139: "NetBIOS", 443: "HTTPS", 445: "SMB", 3389: "RDP", 8080: "HTTP-alt"}
        lines = []
        for port, service in ports.items():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.3)
            try:
                open_ = sock.connect_ex((ip, port)) == 0
            finally:
                sock.close()
            if open_:
                lines.append(f"{port}/tcp  OUVERT  {service}")
        return "\n".join(lines) if lines else "Aucun port courant ouvert détecté."


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("NetScanPy")
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    window = NetScanQt()
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
