//! Best-effort guess of what kind of device something is, from the
//! manufacturer, hostname and MAC address. Purely heuristic.

use std::net::Ipv4Addr;

use crate::scanner::Device;
use crate::vendors::is_randomized;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum DeviceType {
    Router,
    NetworkGear,
    Computer,
    Mobile,
    Printer,
    Media,
    Iot,
    Unknown,
}

impl DeviceType {
    pub fn label(self) -> &'static str {
        match self {
            Self::Router => "Routeur",
            Self::NetworkGear => "Réseau",
            Self::Computer => "Ordinateur",
            Self::Mobile => "Mobile",
            Self::Printer => "Imprimante",
            Self::Media => "Multimédia",
            Self::Iot => "Objet connecté",
            Self::Unknown => "Inconnu",
        }
    }

    /// Short badge text for compact displays.
    pub fn short(self) -> &'static str {
        match self {
            Self::Router => "RT",
            Self::NetworkGear => "NET",
            Self::Computer => "PC",
            Self::Mobile => "MOB",
            Self::Printer => "IMP",
            Self::Media => "TV",
            Self::Iot => "IoT",
            Self::Unknown => "?",
        }
    }
}

fn has(text: &str, words: &[&str]) -> bool {
    words.iter().any(|w| text.contains(w))
}

/// Guess the type of `device`. `gateway` is the router address, if known.
pub fn guess_type(device: &Device, gateway: Option<Ipv4Addr>) -> DeviceType {
    let host = device.hostname.to_lowercase();
    let vendor = device.vendor.to_lowercase();
    let both = format!("{host} {vendor}");

    if gateway == Some(device.ip) || has(&host, &["router", "gateway", "livebox", "freebox", "bbox"]) {
        return DeviceType::Router;
    }
    if has(&host, &["mesh", "switch", "-sg", "access-point", "ap-"])
        || has(&vendor, &["ubiquiti", "tp-link", "netgear", "cisco", "d-link", "mikrotik", "zyxel", "aruba", "tenda"])
    {
        return DeviceType::NetworkGear;
    }
    if has(&both, &["printer", "canon", "epson", "brother", "lexmark", "xerox", "laserjet", "officejet"]) {
        return DeviceType::Printer;
    }
    if has(&both, &["tv", "roku", "chromecast", "sonos", "bravia", "playstation", "xbox", "nintendo", "amazon", "echo", "firetv", "shield"]) {
        return DeviceType::Media;
    }
    if has(&both, &["espressif", "tuya", "shelly", "sonoff", "raspberry", "esp32", "esp8266", "hue", "nest", "ring", "camera", "cam-"]) {
        return DeviceType::Iot;
    }
    if has(&host, &["desktop-", "laptop", "-pc", "pc-", "macbook", "imac", "workstation", "thinkpad", "ubuntu", "debian"])
        || has(&vendor, &["intel", "dell", "lenovo", "asus", "gigabyte", "micro-star", "msi", "realtek", "hewlett", "acer"])
    {
        return DeviceType::Computer;
    }
    if has(&both, &["iphone", "ipad", "android", "galaxy", "redmi", "xiaomi", "huawei", "honor", "oneplus", "oppo", "pixel", "samsung", "phone", "note-"])
        || is_randomized(&device.mac)
    {
        return DeviceType::Mobile;
    }
    DeviceType::Unknown
}

/// The most likely gateway: the `.1` host of the scanned network, when present.
pub fn guess_gateway(devices: &[Device]) -> Option<Ipv4Addr> {
    devices
        .iter()
        .map(|d| d.ip)
        .find(|ip| ip.octets()[3] == 1)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn device(ip: [u8; 4], mac: &str, host: &str, vendor: &str) -> Device {
        let mut d = Device::new(Ipv4Addr::from(ip), mac.into());
        d.hostname = host.into();
        d.vendor = vendor.into();
        d
    }

    #[test]
    fn classifies_common_devices() {
        let gw = Some(Ipv4Addr::new(10, 0, 0, 1));
        assert_eq!(guess_type(&device([10, 0, 0, 1], "80:af:ca:00:00:01", "", ""), gw), DeviceType::Router);
        assert_eq!(guess_type(&device([10, 0, 0, 5], "6c:4c:bc:00:00:01", "TL-SG608E", ""), gw), DeviceType::NetworkGear);
        assert_eq!(guess_type(&device([10, 0, 0, 6], "40:c2:ba:00:00:01", "DESKTOP-6411GOA", ""), gw), DeviceType::Computer);
        assert_eq!(guess_type(&device([10, 0, 0, 7], "7e:2e:8e:00:00:01", "Redmi-Note-14", ""), gw), DeviceType::Mobile);
        assert_eq!(guess_type(&device([10, 0, 0, 8], "00:11:22:00:00:01", "", "Brother Industries"), gw), DeviceType::Printer);
        assert_eq!(guess_type(&device([10, 0, 0, 9], "00:11:22:00:00:02", "", "Espressif Inc."), gw), DeviceType::Iot);
        assert_eq!(guess_type(&device([10, 0, 0, 10], "00:11:22:00:00:03", "", ""), gw), DeviceType::Unknown);
    }

    #[test]
    fn finds_gateway() {
        let list = vec![
            device([10, 0, 0, 5], "aa:aa:aa:aa:aa:01", "", ""),
            device([10, 0, 0, 1], "aa:aa:aa:aa:aa:02", "", ""),
        ];
        assert_eq!(guess_gateway(&list), Some(Ipv4Addr::new(10, 0, 0, 1)));
    }
}
