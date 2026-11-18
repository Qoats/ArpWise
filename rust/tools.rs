//! Per-host tools: latency, port scanning, Wake-on-LAN, system commands.

use std::net::{Ipv4Addr, SocketAddr, TcpStream, UdpSocket};
use std::process::Command;
use std::time::Duration;

use crate::scanner::{parallel_map, Device};

pub const COMMON_PORTS: &[u16] = &[
    21, 22, 23, 25, 53, 80, 110, 139, 143, 443, 445, 554, 631, 1883, 3306, 3389, 5900, 8000,
    8080, 8443, 9100,
];

#[cfg(windows)]
fn hide_window(command: &mut Command) {
    use std::os::windows::process::CommandExt;
    const CREATE_NO_WINDOW: u32 = 0x0800_0000;
    command.creation_flags(CREATE_NO_WINDOW);
}

#[cfg(not(windows))]
fn hide_window(_command: &mut Command) {}

/// Extract the first `=12 ms` / `<1ms` style value from ping output.
fn parse_latency(output: &str) -> Option<f64> {
    let bytes = output.as_bytes();
    for (index, &byte) in bytes.iter().enumerate() {
        if byte != b'=' && byte != b'<' {
            continue;
        }
        let rest = output[index + 1..].trim_start();
        let number: String = rest
            .chars()
            .take_while(|c| c.is_ascii_digit() || *c == '.' || *c == ',')
            .collect();
        if number.is_empty() {
            continue;
        }
        let after = rest[number.len()..].trim_start();
        if after.len() >= 2 && after[..2].eq_ignore_ascii_case("ms") {
            return number.replace(',', ".").parse().ok();
        }
    }
    None
}

/// Round-trip time in ms via the system `ping`, or `None` if unreachable.
pub fn ping_latency(ip: Ipv4Addr, timeout: f64) -> Option<f64> {
    let mut command = Command::new("ping");
    if cfg!(windows) {
        command.args(["-n", "1", "-w", &((timeout * 1000.0) as u64).to_string()]);
    } else {
        command.args(["-c", "1", "-W", &(timeout.round().max(1.0) as u64).to_string()]);
    }
    command.arg(ip.to_string());
    hide_window(&mut command);

    let output = command.output().ok()?;
    parse_latency(&String::from_utf8_lossy(&output.stdout))
}

/// Fill `latency_ms` on every device, in parallel.
pub fn ping_all(devices: &mut [Device], timeout: f64) {
    let ips: Vec<Ipv4Addr> = devices.iter().map(|d| d.ip).collect();
    let results = parallel_map(&ips, 32, |ip| (*ip, ping_latency(*ip, timeout)));
    for (ip, latency) in results {
        if let Some(device) = devices.iter_mut().find(|d| d.ip == ip) {
            device.latency_ms = latency;
        }
    }
}

/// Run a system command (ping, traceroute…) and return stdout + stderr.
pub fn run_command(program: &str, args: &[String]) -> Result<String, String> {
    let mut command = Command::new(program);
    command.args(args);
    hide_window(&mut command);
    let output = command
        .output()
        .map_err(|e| format!("Impossible de lancer {program} : {e}"))?;
    let mut text = String::from_utf8_lossy(&output.stdout).into_owned();
    text.push_str(&String::from_utf8_lossy(&output.stderr));
    let text = text.trim().to_string();
    Ok(if text.is_empty() {
        "Commande terminée sans sortie.".into()
    } else {
        text
    })
}

pub fn ping_command(ip: Ipv4Addr) -> (&'static str, Vec<String>) {
    let count = if cfg!(windows) { "-n" } else { "-c" };
    ("ping", vec![count.into(), "4".into(), ip.to_string()])
}

pub fn traceroute_command(ip: Ipv4Addr) -> (&'static str, Vec<String>) {
    if cfg!(windows) {
        ("tracert", vec!["-d".into(), ip.to_string()])
    } else {
        ("traceroute", vec!["-n".into(), ip.to_string()])
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OpenPort {
    pub port: u16,
    pub service: &'static str,
}

fn service_name(port: u16) -> &'static str {
    match port {
        21 => "FTP",
        22 => "SSH",
        23 => "Telnet",
        25 => "SMTP",
        53 => "DNS",
        80 => "HTTP",
        110 => "POP3",
        139 => "NetBIOS",
        143 => "IMAP",
        443 => "HTTPS",
        445 => "SMB",
        554 => "RTSP",
        631 => "IPP",
        1883 => "MQTT",
        3306 => "MySQL",
        3389 => "RDP",
        5900 => "VNC",
        8000 | 8080 => "HTTP-alt",
        8443 => "HTTPS-alt",
        9100 => "Impression JetDirect",
        _ => "inconnu",
    }
}

/// Parse `22,80,8000-8100` into a sorted, de-duplicated list.
pub fn parse_ports(spec: &str) -> Result<Vec<u16>, String> {
    let mut ports: Vec<u16> = Vec::new();
    for chunk in spec.split(',').map(str::trim).filter(|c| !c.is_empty()) {
        let parse = |text: &str| -> Result<u32, String> {
            text.trim()
                .parse::<u32>()
                .map_err(|_| format!("Port invalide : {chunk}"))
        };
        let (start, end) = match chunk.split_once('-') {
            Some((a, b)) => (parse(a)?, parse(b)?),
            None => (parse(chunk)?, parse(chunk)?),
        };
        let (start, end) = (start.min(end), start.max(end));
        if start < 1 || end > 65535 {
            return Err("Les ports doivent être entre 1 et 65535.".into());
        }
        if ports.len() as u32 + (end - start + 1) > 10_000 {
            return Err("Maximum 10 000 ports par scan.".into());
        }
        ports.extend((start..=end).map(|p| p as u16));
    }
    if ports.is_empty() {
        return Err("Aucun port indiqué.".into());
    }
    ports.sort_unstable();
    ports.dedup();
    Ok(ports)
}

/// TCP connect scan, in parallel. Only scan hosts you are allowed to test.
pub fn scan_ports(ip: Ipv4Addr, ports: &[u16], timeout: Duration) -> Vec<OpenPort> {
    let mut open: Vec<OpenPort> = parallel_map(ports, 128, |&port| {
        let address = SocketAddr::from((ip, port));
        TcpStream::connect_timeout(&address, timeout)
            .is_ok()
            .then(|| OpenPort {
                port,
                service: service_name(port),
            })
    })
    .into_iter()
    .flatten()
    .collect();
    open.sort_by_key(|p| p.port);
    open
}

pub fn format_ports(ip: Ipv4Addr, open: &[OpenPort], scanned: usize) -> String {
    if open.is_empty() {
        return format!("Aucun port ouvert sur {scanned} port(s) testé(s).");
    }
    let mut lines: Vec<String> = open
        .iter()
        .map(|p| format!("{}/tcp  OUVERT  {}", p.port, p.service))
        .collect();
    lines.push(format!(
        "\n{} ouvert(s) sur {scanned} testé(s) · {ip}",
        open.len()
    ));
    lines.join("\n")
}

/// Send a Wake-on-LAN magic packet.
pub fn wake_on_lan(mac: &str, broadcast: Ipv4Addr) -> Result<(), String> {
    let hex: String = mac.chars().filter(char::is_ascii_hexdigit).collect();
    if hex.len() != 12 {
        return Err(format!("Adresse MAC invalide : {mac}"));
    }
    let bytes: Vec<u8> = (0..6)
        .map(|i| u8::from_str_radix(&hex[i * 2..i * 2 + 2], 16).unwrap_or(0))
        .collect();

    let mut packet = vec![0xffu8; 6];
    for _ in 0..16 {
        packet.extend_from_slice(&bytes);
    }

    let socket = UdpSocket::bind("0.0.0.0:0").map_err(|e| e.to_string())?;
    socket.set_broadcast(true).map_err(|e| e.to_string())?;
    socket
        .send_to(&packet, (broadcast, 9))
        .map_err(|e| e.to_string())?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_port_specs() {
        assert_eq!(parse_ports("22, 80,8000-8002").unwrap(), vec![22, 80, 8000, 8001, 8002]);
        assert_eq!(parse_ports("90-88").unwrap(), vec![88, 89, 90]);
        for bad in ["", "abc", "0", "70000", "1-20000"] {
            assert!(parse_ports(bad).is_err(), "{bad}");
        }
    }

    #[test]
    fn parses_ping_output() {
        assert_eq!(parse_latency("Réponse de 1.2.3.4 : octets=32 temps=12 ms TTL=64"), Some(12.0));
        assert_eq!(parse_latency("octets=32 temps<1ms TTL=128"), Some(1.0));
        assert_eq!(parse_latency("64 bytes: icmp_seq=1 ttl=64 time=0.53 ms"), Some(0.53));
        assert_eq!(parse_latency("Délai d'attente de la demande dépassé."), None);
    }

    #[test]
    fn rejects_bad_mac() {
        assert!(wake_on_lan("zz:zz", Ipv4Addr::BROADCAST).is_err());
    }
}
