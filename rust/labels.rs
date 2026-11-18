//! User-defined device labels, keyed by MAC address.

use std::collections::BTreeMap;

use crate::config::{config_dir, normalize_mac};

pub type Labels = BTreeMap<String, String>;

fn data_file() -> std::path::PathBuf {
    config_dir().join("devices.json")
}

pub fn load_labels() -> Labels {
    let Ok(raw) = std::fs::read_to_string(data_file()) else {
        return Labels::new();
    };
    serde_json::from_str::<Labels>(&raw)
        .map(|map| {
            map.into_iter()
                .map(|(mac, label)| (normalize_mac(&mac), label))
                .collect()
        })
        .unwrap_or_default()
}

pub fn save_labels(labels: &Labels) -> Result<(), String> {
    let cleaned: Labels = labels
        .iter()
        .filter(|(_, label)| !label.trim().is_empty())
        .map(|(mac, label)| (normalize_mac(mac), label.trim().to_string()))
        .collect();
    let json = serde_json::to_string_pretty(&cleaned).map_err(|e| e.to_string())?;
    std::fs::write(data_file(), json).map_err(|e| e.to_string())
}

pub fn get_label<'a>(labels: &'a Labels, mac: &str) -> &'a str {
    labels
        .get(&normalize_mac(mac))
        .map(String::as_str)
        .unwrap_or("")
}
