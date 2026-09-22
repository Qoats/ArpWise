from __future__ import annotations

import json
import os
from pathlib import Path


def _normalize_mac(mac: str) -> str:
    return mac.strip().lower().replace("-", ":")


def _data_file() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

    folder = base / "NetScanPy"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "devices.json"


def load_labels() -> dict[str, str]:
    path = _data_file()
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    labels: dict[str, str] = {}

    if isinstance(data, dict):
        for mac, value in data.items():
            if isinstance(mac, str) and isinstance(value, str):
                labels[_normalize_mac(mac)] = value

    return labels


def save_labels(labels: dict[str, str]) -> None:
    path = _data_file()
    normalized = {
        _normalize_mac(mac): label.strip()
        for mac, label in labels.items()
        if label.strip()
    }

    path.write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def get_label(mac: str, labels: dict[str, str] | None = None) -> str:
    data = labels if labels is not None else load_labels()
    return data.get(_normalize_mac(mac), "")


def set_label(mac: str, label: str) -> None:
    labels = load_labels()
    normalized_mac = _normalize_mac(mac)

    if label.strip():
        labels[normalized_mac] = label.strip()
    else:
        labels.pop(normalized_mac, None)

    save_labels(labels)


def remove_label(mac: str) -> None:
    labels = load_labels()
    labels.pop(_normalize_mac(mac), None)
    save_labels(labels)
