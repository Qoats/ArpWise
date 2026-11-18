//! Public IP information (geolocation is approximate).

use serde_json::Value;

#[derive(Debug, Clone, Default)]
pub struct PublicInfo {
    pub ip: String,
    pub city: String,
    pub region: String,
    pub country: String,
    pub latitude: String,
    pub longitude: String,
    pub timezone: String,
    pub asn: String,
    pub organization: String,
}

impl PublicInfo {
    pub fn location(&self) -> String {
        [&self.city, &self.region, &self.country]
            .iter()
            .filter(|part| !part.is_empty())
            .map(|part| part.as_str())
            .collect::<Vec<_>>()
            .join(", ")
    }

    pub fn map_url(&self) -> Option<String> {
        if self.latitude.is_empty() || self.longitude.is_empty() {
            return None;
        }
        Some(format!(
            "https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=12/{lat}/{lon}",
            lat = self.latitude,
            lon = self.longitude
        ))
    }
}

pub fn fetch_public_info() -> Result<PublicInfo, String> {
    let raw = ureq::get("https://ipapi.co/json/")
        .header("Accept", "application/json")
        .header("User-Agent", "ArpWise/0.4")
        .call()
        .map_err(|e| format!("Informations Internet indisponibles : {e}"))?
        .body_mut()
        .read_to_string()
        .map_err(|e| format!("Réponse invalide : {e}"))?;
    let payload: Value =
        serde_json::from_str(&raw).map_err(|e| format!("Réponse invalide : {e}"))?;

    if payload.get("error").and_then(Value::as_bool).unwrap_or(false) {
        let reason = payload
            .get("reason")
            .and_then(Value::as_str)
            .unwrap_or("erreur inconnue");
        return Err(format!("Informations Internet indisponibles : {reason}"));
    }

    let text = |key: &str| -> String {
        match payload.get(key) {
            Some(Value::String(s)) => s.clone(),
            Some(Value::Number(n)) => n.to_string(),
            _ => String::new(),
        }
    };

    Ok(PublicInfo {
        ip: text("ip"),
        city: text("city"),
        region: text("region"),
        country: text("country_name"),
        latitude: text("latitude"),
        longitude: text("longitude"),
        timezone: text("timezone"),
        asn: text("asn"),
        organization: text("org"),
    })
}
