from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .qt_gui import APP_STYLE, NetScanQt


class NetScanQtScrollable(NetScanQt):
    """NetScanQt with a scrollable network inspector for smaller windows."""

    def _build_network_tab(self) -> None:
        # The network panel can be taller than the available inspector area.
        # Keep the tabs fixed and scroll only the panel contents.
        outer = QVBoxLayout(self.network_tab)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet(
            "QScrollArea { background:#111821; border:0; }"
            "QScrollArea > QWidget > QWidget { background:#111821; }"
            "QScrollBar:vertical { background:#0f161f; width:10px; margin:0; }"
            "QScrollBar::handle:vertical { background:#344255; min-height:28px; }"
            "QScrollBar::handle:vertical:hover { background:#465970; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:transparent; }"
        )

        content = QWidget()
        content.setStyleSheet("background:#111821;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 12, 16)
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
        layout.addSpacing(8)

        scroll.setWidget(content)
        outer.addWidget(scroll)


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("NetScanPy")
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)
    app.setFont(QFont("Segoe UI", 10))

    window = NetScanQtScrollable()
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
