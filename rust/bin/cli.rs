use std::net::Ipv4Addr;
use std::path::PathBuf;
use std::process::ExitCode;
use std::time::Duration;

use clap::{Parser, Subcommand};
use arpwise::{
    export::export_devices,
    history::{offline_devices, record_scan},
    labels::load_labels,
    network::{detect_local_network, parse_network},
    scanner::scan_network,
    tools::{COMMON_PORTS, format_ports, parse_ports, ping_all, scan_ports, wake_on_lan},
    vendors::{has_vendor_database, update_vendors},
    Device,
};

#[derive(Parser)]
#[command(name = "arpwise", version, about = "Discover devices on a local IPv4 network.")]
struct Cli {
    /// Private IPv4 CIDR to scan, for example 192.168.1.0/24.
    #[arg(short, long)]
    network: Option<String>,

    /// Neighbour discovery wait time in seconds (Linux).
    #[arg(short, long, default_value_t = 1.0)]
    timeout: f64,

    /// Export results to FILE (.csv or .json).
    #[arg(short, long, value_name = "FILE")]
    output: Option<PathBuf>,

    /// Measure the latency of every device found.
    #[arg(short, long)]
    ping: bool,

    /// Do not read or update the device history.
    #[arg(long)]
    no_history: bool,

    /// Download the IEEE MAC vendor database, then exit.
    #[arg(long)]
    update_vendors: bool,

    #[command(subcommand)]
    command: Option<Command>,
}

#[derive(Subcommand)]
enum Command {
    /// Scan TCP ports of a host you are allowed to test.
    Ports {
        ip: Ipv4Addr,
        /// Ports, e.g. 22,80,8000-8100 (default: common ports).
        #[arg(short, long)]
        range: Option<String>,
    },
    /// Send a Wake-on-LAN packet.
    Wake {
        mac: String,
        #[arg(short, long, default_value = "255.255.255.255")]
        broadcast: Ipv4Addr,
    },
}

fn main() -> ExitCode {
    match run(Cli::parse()) {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("Error: {message}");
            ExitCode::FAILURE
        }
    }
}

fn run(cli: Cli) -> Result<(), String> {
    if cli.timeout <= 0.0 {
        return Err("timeout must be greater than zero.".into());
    }

    if cli.update_vendors {
        let count = update_vendors()?;
        println!("Vendor database updated: {count} entries.");
        return Ok(());
    }

    match cli.command {
        Some(Command::Ports { ip, range }) => {
            let ports = match range {
                Some(spec) => parse_ports(&spec)?,
                None => COMMON_PORTS.to_vec(),
            };
            let open = scan_ports(ip, &ports, Duration::from_millis(500));
            println!("{}", format_ports(ip, &open, ports.len()));
            return Ok(());
        }
        Some(Command::Wake { mac, broadcast }) => {
            wake_on_lan(&mac, broadcast)?;
            println!("Magic packet sent to {mac}.");
            return Ok(());
        }
        None => {}
    }

    let network = match &cli.network {
        Some(value) => parse_network(value)?,
        None => detect_local_network()?,
    };
    let mut devices = scan_network(&network, cli.timeout, None)?;

    if cli.ping {
        ping_all(&mut devices, 1.0);
    }

    let (new_macs, offline) = if cli.no_history {
        (Default::default(), Vec::new())
    } else {
        let (new_macs, history) = record_scan(&devices);
        let offline = offline_devices(&devices, &history);
        (new_macs, offline)
    };

    if let Some(path) = &cli.output {
        export_devices(&devices, path, &load_labels())?;
        eprintln!("Exported {} device(s) to {}", devices.len(), path.display());
    }

    print_devices(&devices, &network.to_string(), &new_macs, &offline);
    if !has_vendor_database() {
        eprintln!("Tip: run 'arpwise --update-vendors' to show device manufacturers.");
    }
    Ok(())
}

fn print_devices(
    devices: &[Device],
    network: &str,
    new_macs: &std::collections::HashSet<String>,
    offline: &[(String, arpwise::history::Entry)],
) {
    println!("\nArpWise\nNetwork: {network}\n");

    let rows: Vec<[String; 6]> = devices
        .iter()
        .map(|d| {
            let is_new = new_macs.contains(&d.mac.to_lowercase().replace('-', ":"));
            [
                d.ip.to_string(),
                d.mac.clone(),
                d.vendor.clone(),
                d.hostname.clone(),
                d.latency_ms.map_or("—".into(), |ms| format!("{ms} ms")),
                if is_new { "NEW".into() } else { String::new() },
            ]
        })
        .collect();

    let headers = ["IP address", "MAC address", "Vendor", "Hostname", "Latency", ""];
    let mut widths = headers.map(|h| h.chars().count());
    for row in &rows {
        for (i, cell) in row.iter().enumerate() {
            widths[i] = widths[i].max(cell.chars().count());
        }
    }

    let line = |cells: &[String]| {
        let text: Vec<String> = cells
            .iter()
            .enumerate()
            .map(|(i, c)| format!("{c:<width$}", width = widths[i]))
            .collect();
        println!("{}", text.join("  ").trim_end());
    };
    line(&headers.map(String::from));
    for row in &rows {
        line(row);
    }

    let count = devices.len();
    println!("\n{count} device{} found.", if count == 1 { "" } else { "s" });
    if !new_macs.is_empty() {
        println!("{} new since last scan.", new_macs.len());
    }
    if !offline.is_empty() {
        println!("\nKnown but not seen now ({}):", offline.len());
        for (mac, entry) in offline.iter().take(10) {
            println!(
                "  {mac}  {}  {}  last seen {}",
                entry.last_ip, entry.vendor, entry.last_seen
            );
        }
    }
}
