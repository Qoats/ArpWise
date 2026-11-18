//! IPv4 network parsing and local network detection.

use std::fmt;
use std::net::Ipv4Addr;

/// A private IPv4 network such as `192.168.1.0/24`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Network {
    base: u32,
    pub prefix: u8,
}

impl Network {
    pub fn new(addr: Ipv4Addr, prefix: u8) -> Result<Self, String> {
        if prefix > 32 {
            return Err(format!("Préfixe invalide : /{prefix}"));
        }
        let mask = Self::mask_for(prefix);
        Ok(Self {
            base: u32::from(addr) & mask,
            prefix,
        })
    }

    fn mask_for(prefix: u8) -> u32 {
        if prefix == 0 { 0 } else { u32::MAX << (32 - prefix) }
    }

    pub fn contains(&self, ip: Ipv4Addr) -> bool {
        u32::from(ip) & Self::mask_for(self.prefix) == self.base
    }

    /// Usable host addresses (network and broadcast excluded for /30 and larger).
    pub fn hosts(&self) -> Vec<Ipv4Addr> {
        let size: u64 = 1u64 << (32 - self.prefix);
        let (first, last) = if self.prefix >= 31 {
            (0u64, size - 1)
        } else {
            (1u64, size - 2)
        };
        (first..=last)
            .map(|offset| Ipv4Addr::from(self.base.wrapping_add(offset as u32)))
            .collect()
    }

    pub fn base_addr(&self) -> Ipv4Addr {
        Ipv4Addr::from(self.base)
    }
}

impl fmt::Display for Network {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}/{}", self.base_addr(), self.prefix)
    }
}

/// Parse a CIDR given by the user. Only private networks of /16 or smaller
/// are accepted, to keep scans on the local network and reasonably sized.
pub fn parse_network(value: &str) -> Result<Network, String> {
    let value = value.trim();
    let (addr, prefix) = value
        .split_once('/')
        .ok_or_else(|| format!("Réseau invalide : {value} (attendu : 192.168.1.0/24)"))?;
    let addr: Ipv4Addr = addr
        .trim()
        .parse()
        .map_err(|_| format!("Adresse IPv4 invalide : {addr}"))?;
    let prefix: u8 = prefix
        .trim()
        .parse()
        .map_err(|_| format!("Préfixe invalide : {prefix}"))?;

    let network = Network::new(addr, prefix)?;
    if !is_private(network.base_addr()) {
        return Err("NetScanPy ne scanne que les réseaux IPv4 privés.".into());
    }
    if network.prefix < 16 {
        return Err("Réseau trop grand : utilisez /16 ou plus petit.".into());
    }
    Ok(network)
}

fn is_private(ip: Ipv4Addr) -> bool {
    ip.is_private()
}

/// The most relevant private interface: closest to a /24 LAN.
#[derive(Debug, Clone)]
pub struct LocalInfo {
    pub interface: String,
    pub ip: Ipv4Addr,
    pub netmask: Ipv4Addr,
    pub network: Network,
}

pub fn local_network_info() -> Option<LocalInfo> {
    let interfaces = if_addrs::get_if_addrs().ok()?;
    let mut candidates: Vec<LocalInfo> = Vec::new();

    for iface in interfaces {
        let if_addrs::IfAddr::V4(v4) = iface.addr else {
            continue;
        };
        if v4.ip.is_loopback() || v4.ip.is_link_local() || !v4.ip.is_private() {
            continue;
        }
        let prefix = u32::from(v4.netmask).count_ones() as u8;
        let Ok(network) = Network::new(v4.ip, prefix) else {
            continue;
        };
        candidates.push(LocalInfo {
            interface: iface.name,
            ip: v4.ip,
            netmask: v4.netmask,
            network,
        });
    }

    candidates.sort_by_key(|c| (i16::from(c.network.prefix) - 24).abs());
    candidates.into_iter().next()
}

pub fn detect_local_network() -> Result<Network, String> {
    local_network_info()
        .map(|info| info.network)
        .ok_or_else(|| "Aucun réseau IPv4 privé utilisable n'a été détecté.".to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_and_lists_hosts() {
        let net = parse_network("192.168.1.77/24").unwrap();
        assert_eq!(net.to_string(), "192.168.1.0/24");
        let hosts = net.hosts();
        assert_eq!(hosts.len(), 254);
        assert_eq!(hosts[0], Ipv4Addr::new(192, 168, 1, 1));
        assert_eq!(hosts[253], Ipv4Addr::new(192, 168, 1, 254));
        assert!(net.contains(Ipv4Addr::new(192, 168, 1, 9)));
        assert!(!net.contains(Ipv4Addr::new(192, 168, 2, 9)));
    }

    #[test]
    fn rejects_public_and_huge_networks() {
        assert!(parse_network("8.8.8.0/24").is_err());
        assert!(parse_network("10.0.0.0/8").is_err());
        assert!(parse_network("pas-un-reseau").is_err());
        assert!(parse_network("192.168.1.0/33").is_err());
    }
}
