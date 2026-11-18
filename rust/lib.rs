//! ArpWise: simple local network scanner (Windows and Linux).
//!
//! No Npcap, no raw sockets: Windows uses the native `SendARP` API, Linux
//! triggers neighbour discovery with UDP and reads `/proc/net/arp`.

pub mod config;
pub mod devicetype;
pub mod export;
pub mod history;
pub mod labels;
pub mod netinfo;
pub mod network;
pub mod scanner;
pub mod settings;
pub mod tools;
pub mod vendors;

pub use scanner::Device;
