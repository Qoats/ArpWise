//! Shared helpers for the per-user config folder.

use std::fs;
use std::path::PathBuf;

/// `%APPDATA%\ArpWise` on Windows, `~/.config/ArpWise` on Linux.
pub fn config_dir() -> PathBuf {
    let base = dirs::config_dir().unwrap_or_else(|| PathBuf::from("."));
    let dir = base.join("ArpWise");

    // The app used to be called NetScanPy: keep the user's labels and history.
    let legacy = base.join("NetScanPy");
    if !dir.exists() && legacy.is_dir() {
        let _ = fs::rename(&legacy, &dir);
    }

    let _ = fs::create_dir_all(&dir);
    dir
}

/// Normalise a MAC address to lowercase, colon separated.
pub fn normalize_mac(mac: &str) -> String {
    mac.trim().to_lowercase().replace('-', ":")
}
