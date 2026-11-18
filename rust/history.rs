//! Persistent device history: first/last seen and new-device detection.

use std::collections::{BTreeMap, HashSet};

use serde::{Deserialize, Serialize};

use crate::config::{config_dir, normalize_mac};
use crate::scanner::Device;

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct Entry {
    pub first_seen: String,
    pub last_seen: String,
    pub last_ip: String,
    pub hostname: String,
    pub vendor: String,
}

pub type History = BTreeMap<String, Entry>;

fn history_file() -> std::path::PathBuf {
    config_dir().join("history.json")
}

pub fn load_history() -> History {
    std::fs::read_to_string(history_file())
        .ok()
        .and_then(|raw| serde_json::from_str(&raw).ok())
        .unwrap_or_default()
}

fn save_history(history: &History) -> Result<(), String> {
    let json = serde_json::to_string_pretty(history).map_err(|e| e.to_string())?;
    std::fs::write(history_file(), json).map_err(|e| e.to_string())
}

fn now() -> String {
    chrono::Local::now().format("%Y-%m-%dT%H:%M:%S").to_string()
}

/// Record a scan. Returns the MACs never seen before and the updated history.
/// On the very first scan nothing is flagged as new.
pub fn record_scan(devices: &[Device]) -> (HashSet<String>, History) {
    let mut history = load_history();
    let first_run = history.is_empty();
    let stamp = now();
    let mut new_macs = HashSet::new();

    for device in devices {
        let mac = normalize_mac(&device.mac);
        if !history.contains_key(&mac) && !first_run {
            new_macs.insert(mac.clone());
        }
        let entry = history.entry(mac).or_insert_with(|| Entry {
            first_seen: stamp.clone(),
            ..Entry::default()
        });
        entry.last_seen = stamp.clone();
        entry.last_ip = device.ip.to_string();
        entry.hostname = device.hostname.clone();
        entry.vendor = device.vendor.clone();
    }

    // Losing the history must not break a scan.
    let _ = save_history(&history);
    (new_macs, history)
}

/// Known devices that did not answer this time, most recently seen first.
pub fn offline_devices(devices: &[Device], history: &History) -> Vec<(String, Entry)> {
    let online: HashSet<String> = devices.iter().map(|d| normalize_mac(&d.mac)).collect();
    let mut offline: Vec<(String, Entry)> = history
        .iter()
        .filter(|(mac, _)| !online.contains(*mac))
        .map(|(mac, entry)| (mac.clone(), entry.clone()))
        .collect();
    offline.sort_by(|a, b| b.1.last_seen.cmp(&a.1.last_seen));
    offline
}
