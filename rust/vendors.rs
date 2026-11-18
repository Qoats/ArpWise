//! MAC vendor lookup from the IEEE OUI registry.
//!
//! The registry is not bundled: `update_vendors` downloads the public IEEE
//! `oui.csv` once and caches it in the config folder.

use std::collections::HashMap;
use std::sync::{Mutex, OnceLock};

use crate::config::config_dir;

const OUI_URL: &str = "https://standards-oui.ieee.org/oui/oui.csv";
pub const PRIVATE_MAC: &str = "Adresse privée (aléatoire)";

fn cache() -> &'static Mutex<Option<HashMap<String, String>>> {
    static CACHE: OnceLock<Mutex<Option<HashMap<String, String>>>> = OnceLock::new();
    CACHE.get_or_init(|| Mutex::new(None))
}

fn oui_file() -> std::path::PathBuf {
    config_dir().join("oui.csv")
}

fn prefix(mac: &str) -> String {
    mac.chars()
        .filter(char::is_ascii_alphanumeric)
        .take(6)
        .collect::<String>()
        .to_uppercase()
}

/// True if the "locally administered" bit is set (phones randomise MACs).
pub fn is_randomized(mac: &str) -> bool {
    let p = prefix(mac);
    p.len() >= 2 && u8::from_str_radix(&p[..2], 16).is_ok_and(|b| b & 0x02 != 0)
}

fn parse_registry(raw: &str) -> HashMap<String, String> {
    let mut reader = csv::ReaderBuilder::new()
        .has_headers(true)
        .flexible(true)
        .from_reader(raw.as_bytes());
    reader
        .records()
        .flatten()
        .filter_map(|record| {
            Some((
                record.get(1)?.trim().to_uppercase(),
                record.get(2)?.trim().to_string(),
            ))
        })
        .collect()
}

pub fn has_vendor_database() -> bool {
    oui_file().exists()
}

/// Vendor name for a MAC, or an empty string if unknown.
pub fn lookup_vendor(mac: &str) -> String {
    if is_randomized(mac) {
        return PRIVATE_MAC.to_string();
    }

    let mut guard = cache().lock().unwrap();
    let table = guard.get_or_insert_with(|| {
        std::fs::read_to_string(oui_file())
            .map(|raw| parse_registry(&raw))
            .unwrap_or_default()
    });
    table.get(&prefix(mac)).cloned().unwrap_or_default()
}

/// Download the IEEE registry. Returns the number of entries.
pub fn update_vendors() -> Result<usize, String> {
    let raw = ureq::get(OUI_URL)
        .header("User-Agent", "NetScanPy/0.4")
        .call()
        .map_err(|e| format!("Téléchargement impossible : {e}"))?
        .body_mut()
        .with_config()
        .limit(64 * 1024 * 1024)
        .read_to_string()
        .map_err(|e| format!("Téléchargement impossible : {e}"))?;

    let table = parse_registry(&raw);
    if table.len() < 1000 {
        return Err("Fichier OUI reçu invalide ou incomplet.".into());
    }
    std::fs::write(oui_file(), &raw).map_err(|e| e.to_string())?;
    let count = table.len();
    *cache().lock().unwrap() = Some(table);
    Ok(count)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn detects_randomized_macs() {
        assert!(is_randomized("da:a1:19:00:00:00"));
        assert!(!is_randomized("3c:22:fb:00:00:00"));
    }

    #[test]
    fn parses_registry_rows() {
        let raw = "Registry,Assignment,Organization Name,Organization Address\n\
                   MA-L,3C22FB,\"Acme, Inc.\",Somewhere\n";
        let table = parse_registry(raw);
        assert_eq!(table.get("3C22FB").map(String::as_str), Some("Acme, Inc."));
    }
}
