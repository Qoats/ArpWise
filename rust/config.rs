//! Shared helpers for the per-user config folder.

use std::fs;
use std::path::PathBuf;

/// `%APPDATA%\NetScanPy` on Windows, `~/.config/NetScanPy` on Linux.
pub fn config_dir() -> PathBuf {
    let dir = dirs::config_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("NetScanPy");
    let _ = fs::create_dir_all(&dir);
    dir
}

/// Normalise a MAC address to lowercase, colon separated.
pub fn normalize_mac(mac: &str) -> String {
    mac.trim().to_lowercase().replace('-', ":")
}
