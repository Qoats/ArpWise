from __future__ import annotations

import ipaddress
import socket
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
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
    color: #e9eff7;
    font-family: "Segoe UI";
    font-size: 13px;
}
QMainWindow, QWidget#root {
    background: #0d131b;
}
QLabel {
    background: transparent;
}
QFrame#topbar,
QFrame#commandbar,
QFrame#statusframe {
    background: #111821;
    border: 0;
}
QFrame#topbar {
    border-bottom: 1px solid #202b38;
}
QFrame#commandbar {
    border-bottom: 1px solid #202b38;
}
QFrame#statusframe {
    background: #0f161f;
    border-bottom: 1px solid #202b38;
}
QLabel#brand {
    font-size: 18px;
    font-weight: 700;
    color: #ffffff;
}
QLabel#muted {
    color: #97a6b8;
}
QLabel#sectionTitle {
    font-size: 14px;
    font-weight: 650;
    color: #f7f9fc;
}
QFrame#panel,
QTabWidget#inspector {
    background: #111821;
    border: 1px solid #202b38;
}
QLabel#emptyState {
    background: #0f161f;
    color: #97a6b8;
    font-size: 14px;
}
QLineEdit {
    min-height: 34px;
    padding: 0 11px;
    background: #0a1119;
    color: #ffffff;
    border: 1px solid #2c3a4b;
    border-radius: 4px;
    selection-background-color: #245d9b;
}
QLineEdit:focus {
    border-color: #3b82f6;
}
QPushButton {
    min-height: 34px;
    padding: 0 13px;
    background: #17212d;
    color: #e6edf5;
    border: 1px solid #2c3a4b;
    border-radius: 4px;
}
QPushButton:hover {
    background: #1d2a38;
    border-color: #41556d;
}
QPushButton:pressed {
    background: #111a24;
}
QPushButton:disabled {
    color: #66778a;
    background: #121a23;
    border-color: #24303d;
}
QPushButton#primary {
    background: #2f7df4;
    color: #ffffff;
    border-color: #2f7df4;
    font-weight: 650;
}
QPushButton#primary:hover {
    background: #478df5;
}
QTableWidget {
    background: #0f161f;
    alternate-background-color: #121b25;
    color: #e4ebf3;
    border: 0;
    gridline-color: transparent;
    selection-background-color: #1f5185;
    selection-color: #ffffff;
    outline: 0;
}
QHeaderView::section {
    background: #17212d;
    color: #bbc7d5;
    padding: 8px 10px;
    border: 0;
    border-bottom: 1px solid #293747;
    font-weight: 600;
}
QTableWidget::item {
    padding: 6px 10px;
    border: 0;
}
QTabWidget#inspector::pane {
    border: 0;
    background: #111821;
}
QTabBar::tab {
    background: #141e29;
    color: #a0afc0;
    border: 0;
    border-bottom: 2px solid transparent;
    padding: 9px 15px;
}
QTabBar::tab:selected {
    color: #ffffff;
    background: #111821;
    border-bottom: 2px solid #3b82f6;
}
QTabBar::tab:hover {
    color: #ffffff;
    background: #1a2633;
}
QTextEdit {
    background: #0a1017;
    color: #e8eef6;
    border: 1px solid #293747;
    border-radius: 4px;
    padding: 10px;
    font-family: Consolas;
    font-size: 12px;
    selection-background-color: #245d9b;
}
QDialog {
    background: #0d131b;
}
"""


class WorkerSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)


class FunctionWorker(QRunnable):
    def __init__(self, fn: Callable[..., object], *args: object) -> None:
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


class OutputDialog(QDialog):
    def __init__(self, parent: QWidget, title: str, output: str) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(760, 500)
        self.setMinimumSize(620, 380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        heading = QLabel(title, objectName="sectionTitle")
        layout.addWidget(heading)

        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setPlainText(output or "Aucune sortie")
        layout.addWidget(self.text, 1)

        close_button = QPushButton("Fermer")
        close_button.setFixedWidth(110)
        close_button.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)


class NetScanQt(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("NetScanPy")
        self.resize(1280, 760)
        self.setMinimumSize(1040, 640)

        self.pool = QThreadPool.globalInstance()
        self._workers: list[FunctionWorker] = []
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
        topbar.setFixedHeight(50)
        top = QHBoxLayout(topbar)
        top.setContentsMargins(20, 0, 20, 0)
        top.setSpacing(0)
        top.addWidget(QLabel("NetScanPy", objectName="brand"))
        top.addStretch(1)
        outer.addWidget(topbar)

        command = QFrame(objectName="commandbar")
        cmd = QHBoxLayout(command)
        cmd.setContentsMargins(20, 10, 20, 10)
        cmd.setSpacing(10)

        network_label = QLabel("Réseau", objectName="muted")
        network_label.setFixedWidth(48)
        self.network_edit = QLineEdit()
        self.network_edit.setPlaceholderText("Détection automatique du réseau…")
        self.scan_button = QPushButton("Scanner", objectName="primary")
        self.scan_button.setFixedWidth(118)
        self.scan_button.clicked.connect(self.start_scan)

        cmd.addWidget(network_label)
        cmd.addWidget(self.network_edit, 1)
        cmd.addWidget(self.scan_button)
        outer.addWidget(command)

        status_frame = QFrame(objectName="statusframe")
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(20, 0, 20, 0)
        status_layout.setSpacing(0)
        status_frame.setFixedHeight(28)
        self.status_line = QLabel("Prêt", objectName="muted")
        status_layout.addWidget(self.status_line)
        outer.addWidget(status_frame)

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(12, 12, 12, 12)
        body_layout.setSpacing(10)

        left = QFrame(objectName="panel")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        header = QFrame()
        header.setStyleSheet("QFrame { background:#111821; border:0; }")
        header.setFixedHeight(52)
        hh = QHBoxLayout(header)
        hh.setContentsMargins(14, 8, 14, 8)
        hh.setSpacing(10)
        hh.addWidget(QLabel("Inventaire réseau", objectName="sectionTitle"))
        hh.addStretch(1)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Rechercher IP, MAC, hôte…")
        self.search.setFixedWidth(260)
        self.search.textChanged.connect(self._render_devices)
        hh.addWidget(self.search)
        left_layout.addWidget(header)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Adresse IP", "Adresse MAC", "Nom d’hôte", "Étiquette"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._selection_changed)

        self.empty_state = QLabel("Analyse du réseau en cours…", objectName="emptyState")
        self.empty_state.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.table_stack = QStackedWidget()
        self.table_stack.setStyleSheet("QStackedWidget { border:0; background:#0f161f; }")
        self.table_stack.addWidget(self.empty_state)
        self.table_stack.addWidget(self.table)
        self.table_stack.setCurrentWidget(self.empty_state)
        left_layout.addWidget(self.table_stack, 1)

        self.tabs = QTabWidget(objectName="inspector")
        self.tabs.setFixedWidth(330)
        self.device_tab = QWidget()
        self.device_tab.setStyleSheet("background:#111821;")
        self.network_tab = QWidget()
        self.network_tab.setStyleSheet("background:#111821;")
        self.tabs.addTab(self.device_tab, "Appareil")
        self.tabs.addTab(self.network_tab, "Réseau")
        self._build_device_tab()
        self._build_network_tab()

        body_layout.addWidget(left, 1)
        body_layout.addWidget(self.tabs)
        outer.addWidget(body, 1)

    def _field(self, layout: QVBoxLayout, name: str) -> QLabel:
        key = QLabel(name, objectName="muted")
        value = QLabel("—")
        value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        value.setWordWrap(True)
        layout.addWidget(key)
        layout.addWidget(value)
        layout.addSpacing(7)
        return value

    def _build_device_tab(self) -> None:
        layout = QVBoxLayout(self.device_tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(3)

        layout.addWidget(QLabel("Appareil", objectName="sectionTitle"))
        layout.addSpacing(8)

        self.dev_ip = self._field(layout, "Adresse IP")
        self.dev_mac = self._field(layout, "Adresse MAC")
        self.dev_host = self._field(layout, "Nom d’hôte")
        self.dev_label = self._field(layout, "Étiquette")

        layout.addSpacing(4)
        layout.addWidget(QLabel("Actions", objectName="muted"))
        layout.addSpacing(2)

        self.ping_btn = QPushButton("Ping", objectName="primary")
        self.trace_btn = QPushButton("Traceroute")
        self.ports_btn = QPushButton("Scanner les ports courants")
        self.browser_btn = QPushButton("Ouvrir dans le navigateur")

        self.ping_btn.clicked.connect(self._ping_selected)
        self.trace_btn.clicked.connect(self._traceroute_selected)
        self.ports_btn.clicked.connect(self._scan_ports)
        self.browser_btn.clicked.connect(self._open_browser)

        for button in (self.ping_btn, self.trace_btn, self.ports_btn, self.browser_btn):
            button.setEnabled(False)
            layout.addWidget(button)

        layout.addStretch(1)

    def _build_network_tab(self) -> None:
        layout = QVBoxLayout(self.network_tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(3)

        layout.addWidget(QLabel("Réseau local", objectName="sectionTitle"))
        layout.addSpacing(7)
        self.net_iface = self._field(layout, "Interface")
        self.net_ip = self._field(layout, "IP locale")
        self.net_mask = self._field(layout, "Masque")
        self.net_subnet = self._field(layout, "Sous-réseau")

        layout.addSpacing(5)
        layout.addWidget(QLabel("Connexion Internet", objectName="sectionTitle"))
        layout.addSpacing(7)
        self.pub_ip = self._field(layout, "IP publique")
        self.pub_loc = self._field(layout, "Localisation")
        self.pub_coords = self._field(layout, "Latitude / longitude")
        self.pub_org = self._field(layout, "Opérateur / organisation")
        self.pub_asn = self._field(layout, "ASN")
        self.pub_tz = self._field(layout, "Fuseau horaire")

        actions = QHBoxLayout()
        actions.setSpacing(6)
        self.refresh_button = QPushButton("Actualiser")
        self.map_button = QPushButton("Carte")
        self.refresh_button.clicked.connect(self._refresh_network_info)
        self.map_button.clicked.connect(self._open_map)
        actions.addWidget(self.refresh_button)
        actions.addWidget(self.map_button)
        layout.addLayout(actions)

        note = QLabel(
            "La géolocalisation IP est approximative et concerne l’IP publique.",
            objectName="muted",
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)

    def _launch_worker(
        self,
        fn: Callable[..., object],
        *args: object,
        finished: Callable[[object], None],
        failed: Callable[[str], None],
    ) -> None:
        worker = FunctionWorker(fn, *args)
        self._workers.append(worker)

        def cleanup() -> None:
            if worker in self._workers:
                self._workers.remove(worker)

        def on_finished(result: object) -> None:
            cleanup()
            finished(result)

        def on_failed(error: str) -> None:
            cleanup()
            failed(error)

        worker.signals.finished.connect(on_finished)
        worker.signals.failed.connect(on_failed)
        self.pool.start(worker)

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
            QMessageBox.warning(
                self, "NetScanPy", "Aucun réseau local IPv4 n’a été détecté."
            )
            return

        try:
            ipaddress.ip_network(network, strict=False)
        except ValueError:
            QMessageBox.warning(self, "NetScanPy", "Réseau IPv4 invalide.")
            return

        self.devices.clear()
        self.table.setRowCount(0)
        self.table_stack.setCurrentWidget(self.empty_state)
        self.empty_state.setText(f"Analyse de {network}…")
        self.scan_button.setEnabled(False)
        self.scan_button.setText("Analyse…")
        self.status_line.setText(f"Analyse de {network}…")

        self._launch_worker(
            scan_network,
            network,
            1.0,
            finished=self._scan_finished,
            failed=self._scan_failed,
        )

    def _scan_finished(self, devices: object) -> None:
        self.devices = list(devices) if isinstance(devices, list) else []
        self._render_devices()
        self.status_line.setText(
            f"{len(self.devices)} appareil(s) détecté(s) · {self.current_network}"
        )
        self.scan_button.setEnabled(True)
        self.scan_button.setText("Scanner")

        if self.devices:
            self.table_stack.setCurrentWidget(self.table)
        else:
            self.empty_state.setText("Aucun appareil détecté sur ce réseau.")
            self.table_stack.setCurrentWidget(self.empty_state)

    def _scan_failed(self, error: str) -> None:
        self.scan_button.setEnabled(True)
        self.scan_button.setText("Scanner")
        self.status_line.setText("Échec du scan")
        self.empty_state.setText("Le scan réseau a échoué.")
        self.table_stack.setCurrentWidget(self.empty_state)
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

        if self.devices and not rows:
            self.empty_state.setText("Aucun appareil ne correspond à la recherche.")
            self.table_stack.setCurrentWidget(self.empty_state)
        elif rows:
            self.table_stack.setCurrentWidget(self.table)
            self.table.selectRow(0)

    def _selected(self) -> SelectedDevice | None:
        row = self.table.currentRow()
        if row < 0:
            return None

        values = [
            self.table.item(row, col).text() if self.table.item(row, col) else ""
            for col in range(4)
        ]
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
        self.refresh_button.setEnabled(False)
        self.status_line.setText("Actualisation des informations réseau…")

        self._launch_worker(
            fetch_public_network_info,
            finished=self._public_info_ready,
            failed=self._public_info_failed,
        )

    def _public_info_ready(self, result: object) -> None:
        self.refresh_button.setEnabled(True)
        if not isinstance(result, PublicNetworkInfo):
            return

        self.public_info = result
        self.pub_ip.setText(result.ip)
        location = ", ".join(
            part
            for part in (result.city, result.region, result.country)
            if part and part != "—"
        ) or "—"
        self.pub_loc.setText(location)
        self.pub_coords.setText(f"{result.latitude}, {result.longitude}")
        self.pub_org.setText(result.organization)
        self.pub_asn.setText(result.asn)
        tz = (
            result.timezone
            if result.utc_offset == "—"
            else f"{result.timezone} ({result.utc_offset})"
        )
        self.pub_tz.setText(tz)
        self.status_line.setText("Informations réseau actualisées")

    def _public_info_failed(self, error: str) -> None:
        self.refresh_button.setEnabled(True)
        for label in (
            self.pub_ip,
            self.pub_loc,
            self.pub_coords,
            self.pub_org,
            self.pub_asn,
            self.pub_tz,
        ):
            label.setText("Indisponible")
        self.status_line.setText(f"Informations Internet indisponibles : {error}")

    def _open_map(self) -> None:
        info = self.public_info
        if not info or info.latitude == "—" or info.longitude == "—":
            QMessageBox.information(
                self,
                "Carte",
                "Les coordonnées publiques ne sont pas encore disponibles.",
            )
            return

        url = QUrl(
            f"https://www.openstreetmap.org/?mlat={info.latitude}&mlon={info.longitude}"
            f"#map=12/{info.latitude}/{info.longitude}"
        )
        QDesktopServices.openUrl(url)

    def _open_browser(self) -> None:
        device = self._selected()
        if not device:
            QMessageBox.information(self, "Navigateur", "Sélectionne d’abord un appareil.")
            return

        self.status_line.setText(f"Ouverture de http://{device.ip}")
        QDesktopServices.openUrl(QUrl(f"http://{device.ip}"))

    def _ping_selected(self) -> None:
        device = self._selected()
        if not device:
            return
        command = [
            "ping",
            "-n" if sys.platform.startswith("win") else "-c",
            "4",
            device.ip,
        ]
        self._run_command(f"Ping · {device.ip}", command)

    def _traceroute_selected(self) -> None:
        device = self._selected()
        if not device:
            return
        command = (
            ["tracert", "-d", device.ip]
            if sys.platform.startswith("win")
            else ["traceroute", "-n", device.ip]
        )
        self._run_command(f"Traceroute · {device.ip}", command)

    def _run_command(self, title: str, command: list[str]) -> None:
        if not command:
            return

        self.status_line.setText(f"{title} en cours…")
        self._set_action_buttons_enabled(False)

        def done(output: object) -> None:
            self._set_action_buttons_enabled(True)
            self.status_line.setText(f"{title} terminé")
            self._show_output(title, str(output))

        def failed(error: str) -> None:
            self._set_action_buttons_enabled(True)
            self.status_line.setText(f"{title} : erreur")
            QMessageBox.critical(self, title, error)

        self._launch_worker(
            self._execute_command,
            command,
            finished=done,
            failed=failed,
        )

    def _set_action_buttons_enabled(self, enabled: bool) -> None:
        has_selection = self._selected() is not None
        state = enabled and has_selection
        for button in (self.ping_btn, self.trace_btn, self.ports_btn, self.browser_btn):
            button.setEnabled(state)

    @staticmethod
    def _execute_command(command: list[str]) -> str:
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
        completed = subprocess.run(
            command,
            capture_output=True,
            creationflags=creationflags,
            timeout=45,
        )
        encoding = "cp850" if sys.platform.startswith("win") else "utf-8"
        stdout = completed.stdout.decode(encoding, errors="replace")
        stderr = completed.stderr.decode(encoding, errors="replace")
        return (stdout + stderr).strip() or "Commande terminée sans sortie."

    def _show_output(self, title: str, output: str) -> None:
        dialog = OutputDialog(self, title, output)
        dialog.exec()

    def _scan_ports(self) -> None:
        device = self._selected()
        if not device:
            return

        title = f"Ports courants · {device.ip}"
        self.status_line.setText(f"Analyse des ports de {device.ip}…")
        self._set_action_buttons_enabled(False)

        def done(result: object) -> None:
            self._set_action_buttons_enabled(True)
            self.status_line.setText(f"Analyse des ports de {device.ip} terminée")
            self._show_output(title, str(result))

        def failed(error: str) -> None:
            self._set_action_buttons_enabled(True)
            self.status_line.setText("Analyse des ports : erreur")
            QMessageBox.critical(self, "Ports", error)

        self._launch_worker(
            self._port_scan,
            device.ip,
            finished=done,
            failed=failed,
        )

    @staticmethod
    def _port_scan(ip: str) -> str:
        ports = {
            21: "FTP",
            22: "SSH",
            23: "Telnet",
            53: "DNS",
            80: "HTTP",
            139: "NetBIOS",
            443: "HTTPS",
            445: "SMB",
            3389: "RDP",
            8080: "HTTP-alt",
        }
        lines: list[str] = []

        for port, service in ports.items():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.35)
            try:
                is_open = sock.connect_ex((ip, port)) == 0
            finally:
                sock.close()

            if is_open:
                lines.append(f"{port}/tcp  OUVERT  {service}")

        return "\n".join(lines) if lines else "Aucun port courant ouvert détecté."


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("NetScanPy")
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)
    app.setFont(QFont("Segoe UI", 10))

    window = NetScanQt()
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
