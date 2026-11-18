//! ARP-based device discovery using native OS features.

use std::net::{IpAddr, Ipv4Addr};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Mutex;
use std::thread;

use serde::{Deserialize, Serialize};

use crate::network::Network;
use crate::vendors;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Device {
    pub ip: Ipv4Addr,
    pub mac: String,
    pub hostname: String,
    pub vendor: String,
    pub latency_ms: Option<f64>,
}

impl Device {
    pub fn new(ip: Ipv4Addr, mac: String) -> Self {
        Self {
            ip,
            mac,
            hostname: String::new(),
            vendor: String::new(),
            latency_ms: None,
        }
    }
}

/// Progress callback: `(done, total)`.
pub type Progress<'a> = &'a (dyn Fn(usize, usize) + Sync);

/// Run `job` over `items` on up to `workers` threads, keeping results.
pub(crate) fn parallel_map<T, R, F>(items: &[T], workers: usize, job: F) -> Vec<R>
where
    T: Sync,
    R: Send,
    F: Fn(&T) -> R + Sync,
{
    let next = AtomicUsize::new(0);
    let results: Mutex<Vec<R>> = Mutex::new(Vec::new());
    let workers = workers.clamp(1, items.len().max(1));

    thread::scope(|scope| {
        for _ in 0..workers {
            scope.spawn(|| {
                loop {
                    let index = next.fetch_add(1, Ordering::Relaxed);
                    let Some(item) = items.get(index) else { break };
                    let value = job(item);
                    results.lock().unwrap().push(value);
                }
            });
        }
    });

    results.into_inner().unwrap()
}

pub fn resolve_hostname(ip: Ipv4Addr) -> String {
    dns_lookup::lookup_addr(&IpAddr::V4(ip)).unwrap_or_default()
}

fn sort_devices(devices: &mut [Device]) {
    devices.sort_by_key(|d| u32::from(d.ip));
}

#[cfg(windows)]
fn discover(
    network: &Network,
    _timeout: f64,
    progress: Option<Progress<'_>>,
) -> Result<Vec<Device>, String> {
    use windows_sys::Win32::NetworkManagement::IpHelper::SendARP;

    let hosts = network.hosts();
    let total = hosts.len();
    let done = AtomicUsize::new(0);

    // SendARP blocks for seconds on empty addresses; threads are cheap, so
    // probe a whole /24 at once.
    let found = parallel_map(&hosts, 256, |ip| {
        let destination = u32::from_ne_bytes(ip.octets());
        let mut mac = [0u8; 8];
        let mut length: u32 = 8;
        // SAFETY: `mac` and `length` outlive the call and `length` matches
        // the buffer size, as SendARP requires.
        let result = unsafe {
            SendARP(destination, 0, mac.as_mut_ptr().cast(), &mut length)
        };
        let finished = done.fetch_add(1, Ordering::Relaxed) + 1;
        if let Some(report) = progress {
            report(finished, total);
        }
        if result != 0 || length == 0 {
            return None;
        }
        let text = mac[..length.min(8) as usize]
            .iter()
            .map(|b| format!("{b:02x}"))
            .collect::<Vec<_>>()
            .join(":");
        Some(Device::new(*ip, text))
    });

    Ok(found.into_iter().flatten().collect())
}

#[cfg(all(unix, not(target_os = "macos")))]
fn discover(
    network: &Network,
    timeout: f64,
    progress: Option<Progress<'_>>,
) -> Result<Vec<Device>, String> {
    use std::net::UdpSocket;
    use std::time::Duration;

    let socket = UdpSocket::bind("0.0.0.0:0").map_err(|e| e.to_string())?;
    socket.set_nonblocking(true).map_err(|e| e.to_string())?;

    let hosts = network.hosts();
    let total = hosts.len();
    for (index, ip) in hosts.iter().enumerate() {
        // The port does not need to be open: the kernel resolves the
        // neighbour with ARP before sending.
        let _ = socket.send_to(&[0u8], (*ip, 9));
        if let Some(report) = progress {
            report(index + 1, total);
        }
    }
    thread::sleep(Duration::from_secs_f64(timeout));

    let table = std::fs::read_to_string("/proc/net/arp")
        .map_err(|_| "La table ARP /proc/net/arp est indisponible.".to_string())?;

    let mut devices = Vec::new();
    for line in table.lines().skip(1) {
        let columns: Vec<&str> = line.split_whitespace().collect();
        if columns.len() < 6 {
            continue;
        }
        let (Ok(ip), flags, mac) = (columns[0].parse::<Ipv4Addr>(), columns[2], columns[3]) else {
            continue;
        };
        // 0x2 means the entry is complete.
        if network.contains(ip) && flags == "0x2" && mac != "00:00:00:00:00:00" {
            devices.push(Device::new(ip, mac.to_lowercase()));
        }
    }
    Ok(devices)
}

#[cfg(not(any(windows, all(unix, not(target_os = "macos")))))]
fn discover(
    _network: &Network,
    _timeout: f64,
    _progress: Option<Progress<'_>>,
) -> Result<Vec<Device>, String> {
    Err("Système non pris en charge : ArpWise fonctionne sous Windows et Linux.".into())
}

/// Discover devices on `network`: ARP, then hostnames and vendors.
pub fn scan_network(
    network: &Network,
    timeout: f64,
    progress: Option<Progress<'_>>,
) -> Result<Vec<Device>, String> {
    let mut devices = discover(network, timeout, progress)?;

    // Reverse DNS can be slow, so resolve all hosts in parallel.
    let ips: Vec<Ipv4Addr> = devices.iter().map(|d| d.ip).collect();
    let names = parallel_map(&ips, 32, |ip| (*ip, resolve_hostname(*ip)));
    for (ip, name) in names {
        if let Some(device) = devices.iter_mut().find(|d| d.ip == ip) {
            device.hostname = name;
        }
    }

    for device in &mut devices {
        device.vendor = vendors::lookup_vendor(&device.mac);
    }

    sort_devices(&mut devices);
    Ok(devices)
}
