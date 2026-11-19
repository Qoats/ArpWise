//! Export scan results to CSV or JSON.

use std::path::Path;

use serde::Serialize;

use crate::labels::{get_label, Labels};
use crate::scanner::Device;

#[derive(Serialize)]
struct Row<'a> {
    ip: String,
    mac: &'a str,
    vendor: &'a str,
    hostname: &'a str,
    label: &'a str,
    latency_ms: Option<f64>,
}

/// Write devices to `path`; the format comes from the file extension.
pub fn export_devices(devices: &[Device], path: &Path, labels: &Labels) -> Result<(), String> {
    let rows: Vec<Row> = devices
        .iter()
        .map(|d| Row {
            ip: d.ip.to_string(),
            mac: &d.mac,
            vendor: &d.vendor,
            hostname: &d.hostname,
            label: get_label(labels, &d.mac),
            latency_ms: d.latency_ms,
        })
        .collect();

    let extension = path
        .extension()
        .and_then(|e| e.to_str())
        .map(str::to_lowercase);

    match extension.as_deref() {
        Some("json") => {
            let json = serde_json::to_string_pretty(&rows).map_err(|e| e.to_string())?;
            std::fs::write(path, json).map_err(|e| e.to_string())
        }
        Some("csv") => {
            // UTF-8 BOM so Excel shows accents correctly.
            let mut writer = csv::Writer::from_writer(Vec::new());
            for row in &rows {
                writer.serialize(row).map_err(|e| e.to_string())?;
            }
            let body = writer.into_inner().map_err(|e| e.to_string())?;
            let mut bytes = vec![0xEF, 0xBB, 0xBF];
            bytes.extend(body);
            std::fs::write(path, bytes).map_err(|e| e.to_string())
        }
        _ => Err("Format non pris en charge : seuls .csv et .json sont acceptés".into()),
    }
}
