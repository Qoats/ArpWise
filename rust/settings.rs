//! User preferences, stored next to the labels and history.

use serde::{Deserialize, Serialize};

use crate::config::config_dir;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default)]
pub struct Settings {
    // Appearance
    pub dark_theme: bool,
    /// Index of the accent colour in the GUI palette.
    pub accent: usize,
    /// Interface zoom factor (1.0 = 100 %).
    pub ui_scale: f32,
    /// Tighter table rows.
    pub compact: bool,
    pub always_on_top: bool,
    /// Open on the network map instead of the list.
    pub map_view: bool,
    /// Show known devices that did not answer the last scan.
    pub show_offline: bool,

    // Scanning
    /// Seconds between automatic scans; 0 = off.
    pub auto_scan_secs: u64,
    pub scan_on_start: bool,
    /// Show the loading screen (at least 5 s) while the first scan runs.
    pub show_splash: bool,
    /// How long to wait for a ping answer, in seconds.
    pub ping_timeout: f64,
    /// Latency (ms) above which a device counts as slow.
    pub slow_ms: f64,

    // Table columns
    pub col_mac: bool,
    pub col_vendor: bool,
    pub col_type: bool,
    pub col_host: bool,
    pub col_latency: bool,
    pub col_label: bool,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            dark_theme: true,
            accent: 0,
            ui_scale: 1.0,
            compact: false,
            always_on_top: false,
            map_view: false,
            show_offline: true,
            auto_scan_secs: 0,
            scan_on_start: true,
            show_splash: true,
            ping_timeout: 1.0,
            slow_ms: 50.0,
            col_mac: true,
            col_vendor: true,
            col_type: true,
            col_host: true,
            col_latency: true,
            col_label: true,
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
