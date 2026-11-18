//! User preferences, stored next to the labels and history.

use serde::{Deserialize, Serialize};

use crate::config::config_dir;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct Settings {
    pub dark_theme: bool,
    /// Seconds between automatic scans; 0 = off.
    pub auto_scan_secs: u64,
    /// Show known devices that did not answer the last scan.
    pub show_offline: bool,
    /// Open on the network map instead of the list.
    pub map_view: bool,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            dark_theme: true,
            auto_scan_secs: 0,
            show_offline: true,
            map_view: false,
        }
    }
}

fn settings_file() -> std::path::PathBuf {
    config_dir().join("settings.json")
}

pub fn load_settings() -> Settings {
    std::fs::read_to_string(settings_file())
        .ok()
        .and_then(|raw| serde_json::from_str(&raw).ok())
        .unwrap_or_default()
}

pub fn save_settings(settings: &Settings) {
    if let Ok(json) = serde_json::to_string_pretty(settings) {
        let _ = std::fs::write(settings_file(), json);
    }
}
