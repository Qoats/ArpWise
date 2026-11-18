#![cfg_attr(windows, windows_subsystem = "windows")]

use std::collections::{HashMap, HashSet};
use std::net::Ipv4Addr;
use std::sync::atomic::{AtomicU32, AtomicUsize, Ordering};
use std::sync::mpsc::{channel, Receiver, Sender};
use std::sync::Arc;
use std::time::{Duration, Instant};

use eframe::egui::{self, Color32, RichText};
use egui_extras::{Column, TableBuilder};
use arpwise::{
    config::{config_dir, normalize_mac},
    devicetype::{guess_gateway, guess_type, DeviceType},
    export::export_devices,
    history::{offline_devices, record_scan, History},
    labels::{get_label, load_labels, save_labels, Labels},
    netinfo::{fetch_public_info, PublicInfo},
    network::{local_network_info, parse_network, LocalInfo},
    scanner::scan_network,
    settings::{load_settings, save_settings, Settings},
    tools::{
        COMMON_PORTS, format_ports, ping_all, ping_command, parse_ports, run_command, scan_ports,
        traceroute_command, wake_on_lan,
    },
    vendors::{has_vendor_database, update_vendors},
    Device,
};

/// The splash screen stays at least this long, and at most `SPLASH_MAX`
/// seconds if the first scan is slow.
const SPLASH_MIN: f32 = 5.0;

/// Accent colours offered in the settings.
const ACCENTS: [(&str, Color32); 6] = [
    ("Bleu", Color32::from_rgb(0x2f, 0x7d, 0xf4)),
    ("Violet", Color32::from_rgb(0x8b, 0x5c, 0xf6)),
    ("Vert", Color32::from_rgb(0x1f, 0xb5, 0x6a)),
    ("Orange", Color32::from_rgb(0xf0, 0x8a, 0x1c)),
    ("Rose", Color32::from_rgb(0xe8, 0x4f, 0x9a)),
    ("Cyan", Color32::from_rgb(0x12, 0xb0, 0xc9)),
];

static ACCENT_RGB: AtomicU32 = AtomicU32::new(0x2f7df4);

fn accent() -> Color32 {
    let v = ACCENT_RGB.load(Ordering::Relaxed);
    Color32::from_rgb((v >> 16) as u8, (v >> 8) as u8, v as u8)
}

fn set_accent(index: usize) {
    let color = ACCENTS.get(index).map_or(DEFAULT_ACCENT, |(_, c)| *c);
    let v = ((color.r() as u32) << 16) | ((color.g() as u32) << 8) | color.b() as u32;
    ACCENT_RGB.store(v, Ordering::Relaxed);
}
const SPLASH_MAX: f32 = 20.0;

const BG: Color32 = Color32::from_rgb(0x0d, 0x13, 0x1b);
const PANEL: Color32 = Color32::from_rgb(0x11, 0x18, 0x21);
const CARD: Color32 = Color32::from_rgb(0x15, 0x1f, 0x2b);
const DEFAULT_ACCENT: Color32 = Color32::from_rgb(0x2f, 0x7d, 0xf4);
const WARN: Color32 = Color32::from_rgb(0xf5, 0xb9, 0x42);
const GOOD: Color32 = Color32::from_rgb(0x3f, 0xb9, 0x50);
const BAD: Color32 = Color32::from_rgb(0xf0, 0x5d, 0x5e);

/// One table row: a device seen now, or a known one that did not answer.
#[derive(Clone)]
struct Row {
    device: Device,
    kind: DeviceType,
    online: bool,
    first_seen: String,
    last_seen: String,
}

struct ScanOutput {
    devices: Vec<Device>,
    new_macs: HashSet<String>,
    history: History,
}

enum Msg {
    Scan(Result<ScanOutput, String>),
    Public(Result<PublicInfo, String>),
    Vendors(Result<usize, String>),
    Output { title: String, result: Result<String, String> },
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum SortBy {
    Ip,
    Mac,
    Vendor,
    Host,
    Latency,
    Label,
    Type,
    Status,
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum Filter {
    All,
    New,
    Slow,
    NoPing,
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum View {
    List,
    Map,
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum Tab {
    Device,
    Network,
    Settings,
}

#[derive(Clone, Copy)]
enum MenuAct {
    ExportCsv,
    ExportJson,
    Quit,
    Rescan,
    UpdateVendors,
    WolDialog,
    HostTool,
    Shortcuts,
    About,
    OpenData,
    ResetSettings,
}

#[derive(Default)]
struct HostTool {
    ip: String,
    ports: String,
}

#[derive(Clone, Copy)]
enum Action {
    CopyIp,
    CopyMac,
    Ping,
    Traceroute,
    Ports,
    Browser,
    Wake,
}

struct App {
    tx: Sender<Msg>,
    rx: Receiver<Msg>,

    network_input: String,
    local: Option<LocalInfo>,
    public: Option<Result<PublicInfo, String>>,

    rows: Vec<Row>,
    new_macs: HashSet<String>,
    labels: Labels,
    selected_mac: Option<String>,
    label_edit: String,

    search: String,
    search_id: egui::Id,
    filter: Filter,
    type_filter: Option<DeviceType>,
    view: View,
    sort: SortBy,
    sort_desc: bool,
    tab: Tab,
    settings: Settings,
    gateway: Option<Ipv4Addr>,
    latency_history: HashMap<String, Vec<f64>>,
    scan_started: Instant,
    scan_secs: f64,
    wol_dialog: Option<String>,
    host_dialog: Option<HostTool>,
    show_shortcuts: bool,
    show_about: bool,
    splash_start: Instant,
    splash_done: bool,
    splash_centered: bool,
    splash_closing: u8,
    logo: egui::TextureHandle,
    splash_bg: Color32,

    scanning: bool,
    busy: bool,
    last_scan: Instant,
    done: Arc<AtomicUsize>,
    total: Arc<AtomicUsize>,
    status: String,

    ports_dialog: Option<String>,
    output: Option<(String, String)>,
}

impl App {
    fn new(cc: &eframe::CreationContext<'_>) -> Self {
        let settings = load_settings();
        set_accent(settings.accent);
        apply_style(&cc.egui_ctx, settings.dark_theme);
        let (logo, splash_bg) = load_logo(&cc.egui_ctx);
        let (show_splash, scan_on_start, scale) =
            (settings.show_splash, settings.scan_on_start, settings.ui_scale);
        let (tx, rx) = channel();
        let local = local_network_info();
        let mut app = Self {
            tx,
            rx,
            network_input: local.as_ref().map(|l| l.network.to_string()).unwrap_or_default(),
            local,
            public: None,
            rows: Vec::new(),
            new_macs: HashSet::new(),
            labels: load_labels(),
            selected_mac: None,
            label_edit: String::new(),
            search: String::new(),
            search_id: egui::Id::unique("arpwise-search"),
            filter: Filter::All,
            type_filter: None,
            view: if settings.map_view { View::Map } else { View::List },
            gateway: None,
            latency_history: HashMap::new(),
            scan_started: Instant::now(),
            scan_secs: 0.0,
            wol_dialog: None,
            host_dialog: None,
            show_shortcuts: false,
            show_about: false,
            splash_start: Instant::now(),
            splash_done: !show_splash,
            splash_centered: false,
            splash_closing: 0,
            logo,
            splash_bg,
            sort: SortBy::Ip,
            sort_desc: false,
            tab: Tab::Device,
            settings,
            scanning: false,
            busy: false,
            last_scan: Instant::now(),
            done: Arc::new(AtomicUsize::new(0)),
            total: Arc::new(AtomicUsize::new(0)),
            status: "Prêt".into(),
            ports_dialog: None,
            output: None,
        };
        app.refresh_public(&cc.egui_ctx);
        if scan_on_start {
            app.start_scan(&cc.egui_ctx);
        }
        if !show_splash {
            cc.egui_ctx.set_zoom_factor(scale);
        }

        // Test hooks, compiled into debug builds only.
        #[cfg(debug_assertions)]
        {
            match std::env::var("ARPWISE_TAB").as_deref() {
                Ok("settings") => app.tab = Tab::Settings,
                Ok("network") => app.tab = Tab::Network,
                _ => {}
            }
            match std::env::var("ARPWISE_DIALOG").as_deref() {
                Ok("about") => app.show_about = true,
                Ok("shortcuts") => app.show_shortcuts = true,
                Ok("tools") => app.host_dialog = Some(HostTool::default()),
                Ok("wol") => app.wol_dialog = Some(String::new()),
                _ => {}
            }
        }
        app
    }

    // ---- background work ---------------------------------------------

    fn start_scan(&mut self, ctx: &egui::Context) {
        if self.scanning {
            return;
        }
        // Re-detect: the machine may have changed network.
        self.local = local_network_info();
        if let Some(local) = &self.local {
            self.network_input = local.network.to_string();
        }
        let network = match parse_network(&self.network_input) {
            Ok(network) => network,
            Err(error) => {
                self.status = error;
                return;
            }
        };

        self.scanning = true;
        self.last_scan = Instant::now();
        self.scan_started = Instant::now();
        self.done.store(0, Ordering::Relaxed);
        self.total.store(network.hosts().len(), Ordering::Relaxed);
        self.status = format!("Analyse de {network}…");

        let (tx, ctx, done) = (self.tx.clone(), ctx.clone(), self.done.clone());
        let ping_timeout = self.settings.ping_timeout;
        std::thread::spawn(move || {
            let report = {
                let ctx = ctx.clone();
                move |finished: usize, _total: usize| {
                    done.store(finished, Ordering::Relaxed);
                    ctx.request_repaint();
                }
            };
            let result = scan_network(&network, 1.0, Some(&report)).map(|mut devices| {
                ping_all(&mut devices, ping_timeout);
                let (new_macs, history) = record_scan(&devices);
                ScanOutput { devices, new_macs, history }
            });
            let _ = tx.send(Msg::Scan(result));
            ctx.request_repaint();
        });
    }

    fn refresh_public(&mut self, ctx: &egui::Context) {
        let (tx, ctx) = (self.tx.clone(), ctx.clone());
        std::thread::spawn(move || {
            let _ = tx.send(Msg::Public(fetch_public_info()));
            ctx.request_repaint();
        });
    }

    fn spawn_output<F>(&mut self, ctx: &egui::Context, title: String, job: F)
    where
        F: FnOnce() -> Result<String, String> + Send + 'static,
    {
        self.busy = true;
        self.status = format!("{title} en cours…");
        let (tx, ctx) = (self.tx.clone(), ctx.clone());
        std::thread::spawn(move || {
            let result = job();
            let _ = tx.send(Msg::Output { title, result });
            ctx.request_repaint();
        });
    }

    fn poll_messages(&mut self) {
        while let Ok(message) = self.rx.try_recv() {
            match message {
                Msg::Scan(Ok(output)) => self.scan_done(output),
                Msg::Scan(Err(error)) => {
                    self.scanning = false;
                    self.status = format!("Échec du scan : {error}");
                }
                Msg::Public(result) => self.public = Some(result),
                Msg::Vendors(result) => {
                    self.busy = false;
                    self.status = match result {
                        Ok(count) => format!("Base des fabricants mise à jour ({count} entrées). Relancez un scan."),
                        Err(error) => error,
                    };
                }
                Msg::Output { title, result } => {
                    self.busy = false;
                    match result {
                        Ok(text) => {
                            self.status = format!("{title} terminé");
                            self.output = Some((title, text));
                        }
                        Err(error) => self.status = format!("{title} : {error}"),
                    }
                }
            }
        }
    }

    fn scan_done(&mut self, output: ScanOutput) {
        self.scanning = false;
        self.last_scan = Instant::now();
        self.scan_secs = self.scan_started.elapsed().as_secs_f64();
        self.gateway = guess_gateway(&output.devices);
        let gateway = self.gateway;

        for device in &output.devices {
            if let Some(ms) = device.latency_ms {
                let series = self.latency_history.entry(device.mac.clone()).or_default();
                series.push(ms);
                if series.len() > 120 {
                    series.remove(0);
                }
            }
        }

        let stamp = |mac: &str| -> (String, String) {
            output
                .history
                .get(&normalize_mac(mac))
                .map(|e| (e.first_seen.clone(), e.last_seen.clone()))
                .unwrap_or_default()
        };

        let mut rows: Vec<Row> = output
            .devices
            .iter()
            .map(|d| {
                let (first_seen, last_seen) = stamp(&d.mac);
                Row { kind: guess_type(d, gateway), device: d.clone(), online: true, first_seen, last_seen }
            })
            .collect();

        for (mac, entry) in offline_devices(&output.devices, &output.history) {
            if let Ok(ip) = entry.last_ip.parse::<Ipv4Addr>() {
                let mut device = Device::new(ip, mac);
                device.hostname = entry.hostname.clone();
                device.vendor = entry.vendor.clone();
                rows.push(Row {
                    kind: guess_type(&device, gateway),
                    device,
                    online: false,
                    first_seen: entry.first_seen.clone(),
                    last_seen: entry.last_seen.clone(),
                });
            }
        }

        let online = output.devices.len();
        self.status = format!(
            "{online} appareil(s) en ligne · {} · scan en {:.1} s",
            self.network_input, self.scan_secs
        );
        if !output.new_macs.is_empty() {
            self.status += &format!(" · {} nouveau(x)", output.new_macs.len());
        }
        if !has_vendor_database() {
            self.status += " · cliquez sur « Fabricants » pour identifier les marques";
        }

        self.rows = rows;
        self.new_macs = output.new_macs;

        let still_there = self
            .selected_mac
            .as_ref()
            .is_some_and(|mac| self.rows.iter().any(|r| &r.device.mac == mac));
        if !still_there {
            self.selected_mac = self.rows.first().map(|r| r.device.mac.clone());
            self.sync_label_edit();
        }
    }

    // ---- data helpers --------------------------------------------------

    fn sync_label_edit(&mut self) {
        self.label_edit = self
            .selected_mac
            .as_deref()
            .map(|mac| get_label(&self.labels, mac).to_string())
            .unwrap_or_default();
    }

    fn selected(&self) -> Option<&Row> {
        let mac = self.selected_mac.as_ref()?;
        self.rows.iter().find(|r| &r.device.mac == mac)
    }

    fn is_new(&self, device: &Device) -> bool {
        self.new_macs.contains(&normalize_mac(&device.mac))
    }

    fn online_devices(&self) -> Vec<Device> {
        self.rows.iter().filter(|r| r.online).map(|r| r.device.clone()).collect()
    }

    /// Indices into `self.rows`, filtered and sorted for display.
    fn visible(&self) -> Vec<usize> {
        let query = self.search.trim().to_lowercase();
        let mut indices: Vec<usize> = (0..self.rows.len())
            .filter(|&i| {
                let row = &self.rows[i];
                let d = &row.device;
                if !row.online && !self.settings.show_offline {
                    return false;
                }
                if self.type_filter.is_some_and(|kind| kind != row.kind) {
                    return false;
                }
                let keep = match self.filter {
                    Filter::All => true,
                    Filter::New => self.is_new(d),
                    Filter::Slow => row.online && d.latency_ms.is_some_and(|ms| ms >= self.settings.slow_ms),
                    Filter::NoPing => row.online && d.latency_ms.is_none(),
                };
                keep && (query.is_empty()
                    || format!(
                        "{} {} {} {} {}",
                        d.ip,
                        d.mac,
                        d.vendor,
                        d.hostname,
                        get_label(&self.labels, &d.mac)
                    )
                    .to_lowercase()
                    .contains(&query))
            })
            .collect();

        indices.sort_by(|&a, &b| {
            let (ra, rb) = (&self.rows[a], &self.rows[b]);
            let (da, db) = (&ra.device, &rb.device);
            let ordering = match self.sort {
                SortBy::Ip => u32::from(da.ip).cmp(&u32::from(db.ip)),
                SortBy::Mac => da.mac.cmp(&db.mac),
                SortBy::Vendor => da.vendor.to_lowercase().cmp(&db.vendor.to_lowercase()),
                SortBy::Host => da.hostname.to_lowercase().cmp(&db.hostname.to_lowercase()),
                SortBy::Latency => da
                    .latency_ms
                    .unwrap_or(f64::MAX)
                    .total_cmp(&db.latency_ms.unwrap_or(f64::MAX)),
                SortBy::Label => get_label(&self.labels, &da.mac)
                    .to_lowercase()
                    .cmp(&get_label(&self.labels, &db.mac).to_lowercase()),
                SortBy::Type => ra.kind.label().cmp(rb.kind.label()),
                SortBy::Status => self.is_new(db).cmp(&self.is_new(da)),
            };
            // Offline devices always go last, whichever the direction.
            ra.online
                .cmp(&rb.online)
                .reverse()
                .then(if self.sort_desc { ordering.reverse() } else { ordering })
        });
        indices
    }

    fn export(&mut self) {
        self.export_as(None);
    }

    /// Save the online devices; `ext` picks the format ("csv" or "json").
    fn export_as(&mut self, ext: Option<&str>) {
        let devices = self.online_devices();
        if devices.is_empty() {
            self.status = "Aucun appareil à exporter.".into();
            return;
        }
        let mut dialog = rfd::FileDialog::new();
        dialog = match ext {
            Some("json") => dialog.set_file_name("arpwise.json").add_filter("JSON", &["json"]),
            Some(_) => dialog.set_file_name("arpwise.csv").add_filter("CSV", &["csv"]),
            None => dialog
                .set_file_name("arpwise.csv")
                .add_filter("CSV", &["csv"])
                .add_filter("JSON", &["json"]),
        };
        let Some(path) = dialog.save_file() else {
            return;
        };
        self.status = match export_devices(&devices, &path, &self.labels) {
            Ok(()) => format!("{} appareil(s) exporté(s) : {}", devices.len(), path.display()),
            Err(error) => error,
        };
    }

    fn update_vendors_async(&mut self, ctx: &egui::Context) {
        if self.busy {
            return;
        }
        self.busy = true;
        self.status = "Téléchargement de la base des fabricants…".into();
        let (tx, ctx) = (self.tx.clone(), ctx.clone());
        std::thread::spawn(move || {
            let _ = tx.send(Msg::Vendors(update_vendors()));
            ctx.request_repaint();
        });
    }

    /// Apply and save a settings change.
    fn settings_changed(&mut self, ctx: &egui::Context, before: &Settings) {
        if self.settings == *before {
            return;
        }
        set_accent(self.settings.accent);
        if self.settings.dark_theme != before.dark_theme || self.settings.accent != before.accent {
            apply_style(ctx, self.settings.dark_theme);
        }
        if self.settings.ui_scale != before.ui_scale {
            ctx.set_zoom_factor(self.settings.ui_scale);
        }
        if self.settings.always_on_top != before.always_on_top {
            ctx.send_viewport_cmd(egui::ViewportCommand::WindowLevel(if self.settings.always_on_top {
                egui::WindowLevel::AlwaysOnTop
            } else {
                egui::WindowLevel::Normal
            }));
        }
        save_settings(&self.settings);
    }

    fn menu_bar(&mut self, ui: &mut egui::Ui, ctx: &egui::Context) {
        let before = self.settings.clone();
        let mut act: Option<MenuAct> = None;

        egui::MenuBar::new().ui(ui, |ui| {
            ui.menu_button("Fichier", |ui| {
                if ui.button("Exporter en CSV…").clicked() {
                    act = Some(MenuAct::ExportCsv);
                }
                if ui.button("Exporter en JSON…").clicked() {
                    act = Some(MenuAct::ExportJson);
                }
                ui.separator();
                if ui.button("Quitter").clicked() {
                    act = Some(MenuAct::Quit);
                }
            });

            ui.menu_button("Affichage", |ui| {
                ui.radio_value(&mut self.view, View::List, "Liste");
                ui.radio_value(&mut self.view, View::Map, "Carte");
                ui.separator();
                ui.radio_value(&mut self.settings.dark_theme, true, "Thème sombre");
                ui.radio_value(&mut self.settings.dark_theme, false, "Thème clair");
                ui.separator();
                ui.menu_button("Zoom", |ui| {
                    for scale in [0.85_f32, 1.0, 1.15, 1.3, 1.5] {
                        ui.radio_value(
                            &mut self.settings.ui_scale,
                            scale,
                            format!("{:.0} %", scale * 100.0),
                        );
                    }
                });
                ui.menu_button("Colonnes", |ui| {
                    ui.checkbox(&mut self.settings.col_mac, "Adresse MAC");
                    ui.checkbox(&mut self.settings.col_vendor, "Fabricant");
                    ui.checkbox(&mut self.settings.col_type, "Type");
                    ui.checkbox(&mut self.settings.col_host, "Nom d’hôte");
                    ui.checkbox(&mut self.settings.col_latency, "Latence");
                    ui.checkbox(&mut self.settings.col_label, "Étiquette");
                });
                ui.separator();
                ui.checkbox(&mut self.settings.compact, "Lignes compactes");
                ui.checkbox(&mut self.settings.show_offline, "Appareils hors ligne");
                ui.checkbox(&mut self.settings.always_on_top, "Toujours au premier plan");
            });

            ui.menu_button("Outils", |ui| {
                if ui.button("Rescanner le réseau   F5").clicked() {
                    act = Some(MenuAct::Rescan);
                }
                if ui.button("Mettre à jour les fabricants").clicked() {
                    act = Some(MenuAct::UpdateVendors);
                }
                ui.separator();
                if ui.button("Réveiller une machine (Wake-on-LAN)…").clicked() {
                    act = Some(MenuAct::WolDialog);
                }
                if ui.button("Ping, traceroute, ports d’une adresse…").clicked() {
                    act = Some(MenuAct::HostTool);
                }
                ui.separator();
                if ui.button("Ouvrir le dossier des données").clicked() {
                    act = Some(MenuAct::OpenData);
                }
                if ui.button("Réinitialiser les réglages").clicked() {
                    act = Some(MenuAct::ResetSettings);
                }
            });

            ui.menu_button("Aide", |ui| {
                if ui.button("Raccourcis clavier").clicked() {
                    act = Some(MenuAct::Shortcuts);
                }
                if ui.button("À propos d’ArpWise").clicked() {
                    act = Some(MenuAct::About);
                }
            });
        });

        self.settings_changed(ctx, &before);

        match act {
            Some(MenuAct::ExportCsv) => self.export_as(Some("csv")),
            Some(MenuAct::ExportJson) => self.export_as(Some("json")),
            Some(MenuAct::Quit) => ctx.send_viewport_cmd(egui::ViewportCommand::Close),
            Some(MenuAct::Rescan) => self.start_scan(ctx),
            Some(MenuAct::UpdateVendors) => self.update_vendors_async(ctx),
            Some(MenuAct::WolDialog) => self.wol_dialog = Some(String::new()),
            Some(MenuAct::HostTool) => {
                self.host_dialog = Some(HostTool {
                    ip: self.selected().map(|r| r.device.ip.to_string()).unwrap_or_default(),
                    ports: String::new(),
                })
            }
            Some(MenuAct::Shortcuts) => self.show_shortcuts = true,
            Some(MenuAct::About) => self.show_about = true,
            Some(MenuAct::OpenData) => open_folder(&config_dir()),
            Some(MenuAct::ResetSettings) => {
                let before = self.settings.clone();
                self.settings = Settings::default();
                self.view = View::List;
                self.settings_changed(ctx, &before);
            }
            None => {}
        }
    }

    fn do_action(&mut self, ctx: &egui::Context, action: Action, device: &Device) {
        let ip = device.ip;
        match action {
            Action::CopyIp => {
                ctx.copy_text(ip.to_string());
                self.status = format!("{ip} copiée dans le presse-papiers");
            }
            Action::CopyMac => {
                ctx.copy_text(device.mac.clone());
                self.status = format!("{} copiée dans le presse-papiers", device.mac);
            }
            Action::Ping => {
                let (program, args) = ping_command(ip);
                self.spawn_output(ctx, format!("Ping · {ip}"), move || run_command(program, &args));
            }
            Action::Traceroute => {
                let (program, args) = traceroute_command(ip);
                self.spawn_output(ctx, format!("Traceroute · {ip}"), move || run_command(program, &args));
            }
            Action::Ports => self.ports_dialog = Some(String::new()),
            Action::Browser => ctx.open_url(egui::OpenUrl::new_tab(format!("http://{ip}"))),
            Action::Wake => {
                self.status = match wake_on_lan(&device.mac, Ipv4Addr::BROADCAST) {
                    Ok(()) => format!("Paquet Wake-on-LAN envoyé à {}", device.mac),
                    Err(error) => error,
                };
            }
        }
    }

    // ---- UI ------------------------------------------------------------

    fn top_bar(&mut self, ui: &mut egui::Ui, ctx: &egui::Context) {
        ui.horizontal(|ui| {
            ui.add_space(6.0);
            ui.label(RichText::new("ArpWise").size(18.0).strong());
            ui.add_space(16.0);
            ui.label(RichText::new("Réseau").color(muted(ui)));
            ui.add(
                egui::TextEdit::singleline(&mut self.network_input)
                    .hint_text("Détection automatique du réseau…")
                    .desired_width(220.0),
            );

            let scan = egui::Button::new(
                RichText::new(if self.scanning { "Analyse…" } else { "Scanner" })
                    .strong()
                    .color(Color32::WHITE),
            )
            .fill(accent())
            .min_size(egui::vec2(96.0, 28.0));
            if ui.add_enabled(!self.scanning, scan).clicked() {
                self.start_scan(ctx);
            }
            if ui.add(egui::Button::new("Exporter…").min_size(egui::vec2(80.0, 28.0))).clicked() {
                self.export();
            }
            let vendors = egui::Button::new("Fabricants").min_size(egui::vec2(80.0, 28.0));
            if ui
                .add_enabled(!self.busy, vendors)
                .on_hover_text("Télécharger la base IEEE des fabricants de cartes réseau")
                .clicked()
            {
                self.busy = true;
                self.status = "Téléchargement de la base des fabricants…".into();
                let (tx, ctx) = (self.tx.clone(), ctx.clone());
                std::thread::spawn(move || {
                    let _ = tx.send(Msg::Vendors(update_vendors()));
                    ctx.request_repaint();
                });
            }
        });

        if self.scanning {
            let total = self.total.load(Ordering::Relaxed).max(1);
            let done = self.done.load(Ordering::Relaxed);
            ui.add(
                egui::ProgressBar::new(done as f32 / total as f32)
                    .text(format!("{done}/{total}"))
                    .desired_height(14.0),
            );
        }
    }

    fn stats(&self, ui: &mut egui::Ui) {
        let online: Vec<&Row> = self.rows.iter().filter(|r| r.online).collect();
        let offline = self.rows.len() - online.len();
        let latencies: Vec<f64> = online.iter().filter_map(|r| r.device.latency_ms).collect();
        let average = if latencies.is_empty() {
            "—".to_string()
        } else {
            format!("{:.0} ms", latencies.iter().sum::<f64>() / latencies.len() as f64)
        };

        ui.horizontal(|ui| {
            card(ui, "En ligne", &online.len().to_string(), GOOD);
            card(ui, "Nouveaux", &self.new_macs.len().to_string(), WARN);
            card(ui, "Hors ligne", &offline.to_string(), muted(ui));
            card(ui, "Latence moyenne", &average, accent());
        });
    }

    fn table(&mut self, ui: &mut egui::Ui, ctx: &egui::Context) {
        self.stats(ui);
        ui.add_space(8.0);

        let slow_label = format!("Lents (≥ {:.0} ms)", self.settings.slow_ms);
        ui.horizontal(|ui| {
            for (filter, text) in [
                (Filter::All, "Tous"),
                (Filter::New, "Nouveaux"),
                (Filter::Slow, slow_label.as_str()),
                (Filter::NoPing, "Sans réponse au ping"),
            ] {
                ui.selectable_value(&mut self.filter, filter, text);
            }
            egui::ComboBox::from_id_salt("type_filter")
                .selected_text(self.type_filter.map_or("Tous les types", |k| k.label()))
                .show_ui(ui, |ui| {
                    ui.selectable_value(&mut self.type_filter, None, "Tous les types");
                    for kind in [
                        DeviceType::Router,
                        DeviceType::NetworkGear,
                        DeviceType::Computer,
                        DeviceType::Mobile,
                        DeviceType::Printer,
                        DeviceType::Media,
                        DeviceType::Iot,
                        DeviceType::Unknown,
                    ] {
                        ui.selectable_value(&mut self.type_filter, Some(kind), kind.label());
                    }
                });
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                ui.selectable_value(&mut self.view, View::Map, "Carte");
                ui.selectable_value(&mut self.view, View::List, "Liste");
                ui.add(
                    egui::TextEdit::singleline(&mut self.search)
                        .id(self.search_id)
                        .hint_text("Rechercher IP, MAC, hôte…  (Ctrl+F)")
                        .desired_width(240.0),
                );
            });
        });
        ui.add_space(6.0);

        let visible = self.visible();
        if visible.is_empty() {
            ui.centered_and_justified(|ui| {
                let text = if self.scanning {
                    "Analyse du réseau en cours…"
                } else if self.rows.is_empty() {
                    "Aucun appareil détecté sur ce réseau."
                } else {
                    "Aucun appareil ne correspond au filtre."
                };
                ui.label(RichText::new(text).color(muted(ui)).size(14.0));
            });
            return;
        }

        if self.view == View::Map {
            self.map(ui, &visible);
            return;
        }

        let mut clicked: Option<String> = None;
        let mut sort_request: Option<SortBy> = None;
        let mut pending: Option<(Action, Device)> = None;

        let st = self.settings.clone();
        let row_height = if st.compact { 24.0 } else { 32.0 };
        let slow = st.slow_ms;

        let mut cols: Vec<(SortBy, &str, Column)> =
            vec![(SortBy::Ip, "Adresse IP", Column::auto().at_least(100.0))];
        if st.col_mac {
            cols.push((SortBy::Mac, "Adresse MAC", Column::auto().at_least(135.0)));
        }
        if st.col_vendor {
            cols.push((SortBy::Vendor, "Fabricant", Column::initial(120.0).at_least(60.0).clip(true)));
        }
        if st.col_type {
            cols.push((SortBy::Type, "Type", Column::auto().at_least(90.0)));
        }
        if st.col_host {
            cols.push((SortBy::Host, "Nom d’hôte", Column::initial(130.0).at_least(60.0).clip(true)));
        }
        if st.col_latency {
            cols.push((SortBy::Latency, "Latence", Column::auto().at_least(80.0)));
        }
        if st.col_label {
            cols.push((SortBy::Label, "Étiquette", Column::initial(110.0).at_least(60.0).clip(true)));
        }
        cols.push((SortBy::Status, "", Column::remainder().at_least(70.0)));

        let mut builder = TableBuilder::new(ui)
            .striped(true)
            .sense(egui::Sense::click())
            .cell_layout(egui::Layout::left_to_right(egui::Align::Center));
        for (_, _, column) in &cols {
            builder = builder.column(*column);
        }

        builder
            .header(28.0, |mut header| {
                for (column, title, _) in &cols {
                    header.col(|ui| {
                        let arrow = if self.sort == *column {
                            if self.sort_desc { " ▼" } else { " ▲" }
                        } else {
                            ""
                        };
                        let text = RichText::new(format!("{title}{arrow}")).strong().color(muted(ui));
                        if ui.add(egui::Label::new(text).sense(egui::Sense::click())).clicked() {
                            sort_request = Some(*column);
                        }
                    });
                }
            })
            .body(|body| {
                body.rows(row_height, visible.len(), |mut row| {
                    let item = &self.rows[visible[row.index()]];
                    let device = &item.device;
                    row.set_selected(self.selected_mac.as_deref() == Some(device.mac.as_str()));

                    let dim = |ui: &egui::Ui, text: &str| {
                        let color = if item.online { ui.visuals().text_color() } else { muted(ui) };
                        RichText::new(text).color(color)
                    };

                    for (column, _, _) in &cols {
                        row.col(|ui| match *column {
                            SortBy::Ip => {
                                ui.label(dim(ui, &device.ip.to_string()));
                            }
                            SortBy::Mac => {
                                ui.label(dim(ui, &device.mac).monospace());
                            }
                            SortBy::Vendor => {
                                ui.label(dim(ui, &device.vendor));
                            }
                            SortBy::Type => {
                                let color = if item.online { type_color(item.kind) } else { muted(ui) };
                                ui.label(RichText::new(item.kind.label()).color(color));
                            }
                            SortBy::Host => {
                                let host = if device.hostname.is_empty() { "—" } else { &device.hostname };
                                ui.label(dim(ui, host));
                            }
                            SortBy::Latency => {
                                if item.online {
                                    ui.horizontal(|ui| {
                                        ui.spacing_mut().item_spacing.x = 4.0;
                                        ui.label(
                                            RichText::new("●").color(latency_color(device.latency_ms, slow)),
                                        );
                                        ui.label(
                                            device.latency_ms.map_or("—".to_string(), |ms| format!("{ms:.0} ms")),
                                        );
                                    });
                                } else {
                                    ui.label(RichText::new("hors ligne").color(muted(ui)));
                                }
                            }
                            SortBy::Label => {
                                ui.label(get_label(&self.labels, &device.mac));
                            }
                            SortBy::Status => {
                                if self.is_new(device) {
                                    ui.label(RichText::new("NOUVEAU").color(WARN).strong());
                                }
                            }
                        });
                    }

                    let response = row.response();
                    if response.clicked() || response.secondary_clicked() {
                        clicked = Some(device.mac.clone());
                    }
                    response.context_menu(|ui| {
                        let entries = [
                            (Action::CopyIp, "Copier l’IP"),
                            (Action::CopyMac, "Copier la MAC"),
                            (Action::Ping, "Ping"),
                            (Action::Traceroute, "Traceroute"),
                            (Action::Ports, "Scanner les ports…"),
                            (Action::Browser, "Ouvrir dans le navigateur"),
                            (Action::Wake, "Réveiller (Wake-on-LAN)"),
                        ];
                        for (action, text) in entries {
                            if ui.button(text).clicked() {
                                pending = Some((action, device.clone()));
                                ui.close();
                            }
                        }
                    });
                });
            });

        if let Some(column) = sort_request {
            if self.sort == column {
                self.sort_desc = !self.sort_desc;
            } else {
                self.sort = column;
                self.sort_desc = false;
            }
        }
        if let Some(mac) = clicked {
            self.selected_mac = Some(mac);
            self.sync_label_edit();
            self.tab = Tab::Device;
        }
        if let Some((action, device)) = pending {
            self.selected_mac = Some(device.mac.clone());
            self.sync_label_edit();
            self.do_action(ctx, action, &device);
        }
    }

    /// Radar-style map: the router in the middle, devices around it, placed
    /// further out when they answer more slowly.
    fn map(&mut self, ui: &mut egui::Ui, visible: &[usize]) {
        let (response, painter) = ui.allocate_painter(ui.available_size(), egui::Sense::click());
        let rect = response.rect;
        let center = rect.center();
        let radius = (rect.size().min_elem() * 0.5 - 40.0).max(80.0);
        let line = ui.visuals().widgets.noninteractive.bg_stroke.color;
        let text_color = ui.visuals().text_color();
        let weak = muted(ui);
        let slow = self.settings.slow_ms;

        for fraction in [0.35, 0.65, 1.0] {
            painter.circle_stroke(center, radius * fraction, egui::Stroke::new(1.0, line));
        }

        // The gateway sits in the middle; everyone else around it.
        let hub = visible.iter().copied().find(|&i| Some(self.rows[i].device.ip) == self.gateway);
        let others: Vec<usize> = visible.iter().copied().filter(|&i| Some(i) != hub).collect();

        struct Node {
            index: usize,
            pos: egui::Pos2,
        }
        let mut nodes: Vec<Node> = Vec::new();
        let count = others.len().max(1) as f32;
        for (n, &index) in others.iter().enumerate() {
            let row = &self.rows[index];
            let distance = match (row.online, row.device.latency_ms) {
                (false, _) => 1.0,
                (true, None) => 0.85,
                (true, Some(ms)) if ms < slow * 0.4 => 0.38,
                (true, Some(ms)) if ms < slow * 1.6 => 0.68,
                (true, Some(_)) => 0.95,
            };
            let angle = std::f32::consts::TAU * n as f32 / count - std::f32::consts::FRAC_PI_2;
            nodes.push(Node {
                index,
                pos: center + egui::vec2(angle.cos(), angle.sin()) * radius * distance,
            });
        }

        let pointer = response.hover_pos();
        let mut hovered: Option<usize> = None;
        let mut clicked_mac: Option<String> = None;

        for node in &nodes {
            let alpha = if self.rows[node.index].online { 70 } else { 30 };
            painter.line_segment(
                [center, node.pos],
                egui::Stroke::new(1.0, Color32::from_rgba_unmultiplied(line.r(), line.g(), line.b(), alpha)),
            );
        }

        // Hub.
        let hub_row = hub.map(|i| &self.rows[i]);
        painter.circle_filled(center, 22.0, accent());
        painter.text(
            center,
            egui::Align2::CENTER_CENTER,
            hub_row.map_or("LAN", |r| r.kind.short()),
            egui::FontId::proportional(12.0),
            Color32::WHITE,
        );
        painter.text(
            center + egui::vec2(0.0, 34.0),
            egui::Align2::CENTER_CENTER,
            hub_row.map_or("Réseau".to_string(), |r| r.device.ip.to_string()),
            egui::FontId::proportional(11.0),
            weak,
        );
        if let (Some(pos), Some(i)) = (pointer, hub) {
            if pos.distance(center) < 22.0 {
                hovered = Some(i);
            }
        }

        for node in &nodes {
            let row = &self.rows[node.index];
            let selected = self.selected_mac.as_deref() == Some(row.device.mac.as_str());
            let color = if row.online { latency_color(row.device.latency_ms, slow) } else { Color32::from_gray(0x6a) };

            if pointer.is_some_and(|p| p.distance(node.pos) < 17.0) {
                hovered = Some(node.index);
            }
            if selected || hovered == Some(node.index) {
                painter.circle_stroke(node.pos, 20.0, egui::Stroke::new(2.0, accent()));
            }
            painter.circle_filled(node.pos, 15.0, color);
            painter.text(
                node.pos,
                egui::Align2::CENTER_CENTER,
                row.kind.short(),
                egui::FontId::proportional(9.0),
                Color32::BLACK,
            );

            let label = get_label(&self.labels, &row.device.mac);
            let name = if !label.is_empty() {
                label.to_string()
            } else if !row.device.hostname.is_empty() {
                row.device.hostname.clone()
            } else {
                row.device.ip.to_string()
            };
            painter.text(
                node.pos + egui::vec2(0.0, 26.0),
                egui::Align2::CENTER_CENTER,
                name,
                egui::FontId::proportional(11.0),
                if row.online { text_color } else { weak },
            );
        }

        if let Some(index) = hovered {
            let row = &self.rows[index];
            let device = &row.device;
            response.clone().on_hover_ui_at_pointer(|ui| {
                ui.label(RichText::new(row.kind.label()).strong());
                ui.label(format!("{}  ·  {}", device.ip, device.mac));
                if !device.vendor.is_empty() {
                    ui.label(&device.vendor);
                }
                if !device.hostname.is_empty() {
                    ui.label(&device.hostname);
                }
                ui.label(if row.online {
                    device.latency_ms.map_or("en ligne".to_string(), |ms| format!("{ms:.0} ms"))
                } else {
                    "hors ligne".to_string()
                });
            });
            if response.clicked() {
                clicked_mac = Some(device.mac.clone());
            }
        }

        // Legend.
        let legend = [
            (GOOD, format!("< {:.0} ms", slow * 0.4)),
            (WARN, format!("< {:.0} ms", slow * 1.6)),
            (BAD, format!("≥ {:.0} ms", slow * 1.6)),
            (Color32::from_gray(0x6a), "hors ligne".to_string()),
        ];
        for (n, (color, text)) in legend.iter().enumerate() {
            let y = rect.bottom() - 14.0 - 16.0 * (legend.len() - 1 - n) as f32;
            painter.circle_filled(egui::pos2(rect.left() + 14.0, y), 5.0, *color);
            painter.text(
                egui::pos2(rect.left() + 26.0, y),
                egui::Align2::LEFT_CENTER,
                text.as_str(),
                egui::FontId::proportional(11.0),
                weak,
            );
        }

        if let Some(mac) = clicked_mac {
            self.selected_mac = Some(mac);
            self.sync_label_edit();
            self.tab = Tab::Device;
        }
    }

    /// Small borderless loading window, exactly the size of the logo.
    fn splash(&self, ui: &mut egui::Ui, t: f32) {
        egui::CentralPanel::default()
            .frame(egui::Frame::new().fill(self.splash_bg))
            .show(ui, |ui| {
                let rect = ui.max_rect();
                let alpha = ((t / 0.5).clamp(0.0, 1.0) * 255.0) as u8;
                ui.put(
                    rect,
                    egui::Image::new(egui::load::SizedTexture::new(self.logo.id(), rect.size()))
                        .tint(Color32::from_white_alpha(alpha)),
                );

                // Windows 10 style loading animation, as a line: five dots
                // slide from left to right, fast at the edges and slow in
                // the middle, one after the other.
                let ink = Color32::from_rgb(0x2a, 0x20, 0x1a);
                let y = rect.bottom() - 12.0;
                let cycle = (t / 2.2).fract();
                for i in 0..5 {
                    let p = cycle * 1.5 - i as f32 * 0.09;
                    if !(0.0..=1.0).contains(&p) {
                        continue;
                    }
                    let eased = p + 0.9 * (std::f32::consts::TAU * p).sin() / std::f32::consts::TAU;
                    let x = rect.left() + 6.0 + (rect.width() - 12.0) * eased.clamp(0.0, 1.0);
                    ui.painter().circle_filled(egui::pos2(x, y), 2.5, ink.gamma_multiply(alpha as f32 / 255.0));
                }
            });
    }

    fn side_panel(&mut self, ui: &mut egui::Ui, ctx: &egui::Context) {
        ui.horizontal(|ui| {
            ui.selectable_value(&mut self.tab, Tab::Device, "Appareil");
            ui.selectable_value(&mut self.tab, Tab::Network, "Réseau");
            ui.selectable_value(&mut self.tab, Tab::Settings, "Réglages");
        });
        ui.separator();

        egui::ScrollArea::vertical().show(ui, |ui| match self.tab {
            Tab::Device => self.device_tab(ui, ctx),
            Tab::Network => self.network_tab(ui, ctx),
            Tab::Settings => self.settings_tab(ui, ctx),
        });
    }

    fn device_tab(&mut self, ui: &mut egui::Ui, ctx: &egui::Context) {
        let Some(row) = self.selected().cloned() else {
            ui.label(RichText::new("Sélectionnez un appareil.").color(muted(ui)));
            return;
        };
        let device = row.device.clone();

        ui.horizontal(|ui| {
            ui.label(RichText::new("Appareil").size(14.0).strong());
            let (text, color) = if row.online { ("en ligne", GOOD) } else { ("hors ligne", BAD) };
            ui.label(RichText::new(format!("● {text}")).color(color));
        });
        ui.add_space(6.0);
        field(ui, "Adresse IP", &device.ip.to_string());
        field(ui, "Adresse MAC", &device.mac);
        field(ui, "Type", row.kind.label());
        field(ui, "Fabricant", if device.vendor.is_empty() { "Inconnu" } else { &device.vendor });
        field(ui, "Nom d’hôte", if device.hostname.is_empty() { "Inconnu" } else { &device.hostname });
        if row.online {
            field(ui, "Latence", &device.latency_ms.map_or("—".into(), |ms| format!("{ms:.0} ms")));
        }
        if let Some(series) = self.latency_history.get(&device.mac) {
            if series.len() >= 2 {
                sparkline(ui, series);
            }
        }
        field(ui, "Premier passage", &pretty_time(&row.first_seen));
        field(ui, "Dernier passage", &pretty_time(&row.last_seen));

        ui.label(RichText::new("Étiquette").color(muted(ui)).small());
        ui.horizontal(|ui| {
            ui.add(egui::TextEdit::singleline(&mut self.label_edit).desired_width(170.0));
            if ui.button("Enregistrer").clicked() {
                self.labels.insert(normalize_mac(&device.mac), self.label_edit.trim().to_string());
                self.status = match save_labels(&self.labels) {
                    Ok(()) => "Étiquette enregistrée".into(),
                    Err(error) => error,
                };
            }
        });

        ui.add_space(10.0);
        ui.label(RichText::new("Actions").color(muted(ui)).small());
        let width = ui.available_width();
        let entries = [
            (Action::Ping, "Ping", !self.busy),
            (Action::Traceroute, "Traceroute", !self.busy),
            (Action::Ports, "Scanner les ports…", !self.busy),
            (Action::Browser, "Ouvrir dans le navigateur", true),
            (Action::Wake, "Réveiller (Wake-on-LAN)", true),
            (Action::CopyIp, "Copier l’IP", true),
            (Action::CopyMac, "Copier la MAC", true),
        ];
        for (action, text, enabled) in entries {
            let button = egui::Button::new(text).min_size(egui::vec2(width, 30.0));
            if ui.add_enabled(enabled, button).clicked() {
                self.do_action(ctx, action, &device);
            }
        }
    }

    fn network_tab(&mut self, ui: &mut egui::Ui, ctx: &egui::Context) {
        ui.label(RichText::new("Réseau local").size(14.0).strong());
        ui.add_space(6.0);
        match &self.local {
            Some(local) => {
                field(ui, "Interface", &local.interface);
                field(ui, "IP locale", &local.ip.to_string());
                field(ui, "Masque", &local.netmask.to_string());
                field(ui, "Sous-réseau", &local.network.to_string());
            }
            None => {
                ui.label(RichText::new("Aucun réseau local détecté.").color(muted(ui)));
            }
        }

        ui.add_space(8.0);
        ui.label(RichText::new("Connexion Internet").size(14.0).strong());
        ui.add_space(6.0);
        match &self.public {
            None => {
                ui.label(RichText::new("Chargement…").color(muted(ui)));
            }
            Some(Err(error)) => {
                ui.label(RichText::new(error).color(muted(ui)));
            }
            Some(Ok(info)) => {
                field(ui, "IP publique", &info.ip);
                field(ui, "Localisation", &info.location());
                field(ui, "Latitude / longitude", &format!("{}, {}", info.latitude, info.longitude));
                field(ui, "Opérateur / organisation", &info.organization);
                field(ui, "ASN", &info.asn);
                field(ui, "Fuseau horaire", &info.timezone);
            }
        }

        ui.horizontal(|ui| {
            if ui.button("Actualiser").clicked() {
                self.public = None;
                self.refresh_public(ctx);
            }
            let map_url = match &self.public {
                Some(Ok(info)) => info.map_url(),
                _ => None,
            };
            if ui.add_enabled(map_url.is_some(), egui::Button::new("Carte")).clicked() {
                if let Some(url) = map_url {
                    ctx.open_url(egui::OpenUrl::new_tab(url));
                }
            }
        });
        ui.add_space(4.0);
        ui.label(
            RichText::new("La géolocalisation IP est approximative et concerne l’IP publique.")
                .color(muted(ui))
                .small(),
        );
    }

    fn settings_tab(&mut self, ui: &mut egui::Ui, ctx: &egui::Context) {
        ui.label(RichText::new("Réglages").size(15.0).strong());
        ui.add_space(6.0);

        let before = self.settings.clone();

        egui::CollapsingHeader::new("Apparence").default_open(true).show(ui, |ui| {
            ui.label(RichText::new("Thème").color(muted(ui)).small());
            ui.horizontal(|ui| {
                ui.selectable_value(&mut self.settings.dark_theme, true, "Sombre");
                ui.selectable_value(&mut self.settings.dark_theme, false, "Clair");
            });
            ui.add_space(6.0);

            ui.label(RichText::new("Couleur d’accent").color(muted(ui)).small());
            ui.horizontal_wrapped(|ui| {
                for (index, (name, color)) in ACCENTS.iter().enumerate() {
                    let (rect, response) =
                        ui.allocate_exact_size(egui::vec2(28.0, 28.0), egui::Sense::click());
                    ui.painter().circle_filled(rect.center(), 11.0, *color);
                    if self.settings.accent == index {
                        ui.painter().circle_stroke(
                            rect.center(),
                            14.0,
                            egui::Stroke::new(2.0, ui.visuals().text_color()),
                        );
                    }
                    if response.on_hover_text(*name).clicked() {
                        self.settings.accent = index;
                    }
                }
            });
            ui.add_space(6.0);

            ui.label(RichText::new("Zoom de l’interface").color(muted(ui)).small());
            ui.add(
                egui::Slider::new(&mut self.settings.ui_scale, 0.8..=1.6)
                    .custom_formatter(|v, _| format!("{:.0} %", v * 100.0))
                    .step_by(0.05),
            );
            ui.add_space(4.0);
            ui.checkbox(&mut self.settings.compact, "Lignes compactes");
            ui.checkbox(&mut self.settings.show_offline, "Afficher les appareils hors ligne");
            ui.checkbox(&mut self.settings.always_on_top, "Toujours au premier plan");
        });

        egui::CollapsingHeader::new("Analyse").default_open(true).show(ui, |ui| {
            ui.label(RichText::new("Scan automatique").color(muted(ui)).small());
            egui::ComboBox::from_id_salt("auto_scan")
                .selected_text(match self.settings.auto_scan_secs {
                    0 => "Désactivé".to_string(),
                    s if s < 60 => format!("Toutes les {s} s"),
                    s => format!("Toutes les {} min", s / 60),
                })
                .show_ui(ui, |ui| {
                    for (secs, text) in [
                        (0, "Désactivé"),
                        (30, "Toutes les 30 s"),
                        (60, "Toutes les minutes"),
                        (300, "Toutes les 5 minutes"),
                        (900, "Toutes les 15 minutes"),
                    ] {
                        ui.selectable_value(&mut self.settings.auto_scan_secs, secs, text);
                    }
                });
            ui.add_space(6.0);

            ui.label(RichText::new("Délai de réponse du ping").color(muted(ui)).small());
            ui.add(
                egui::Slider::new(&mut self.settings.ping_timeout, 0.3..=3.0)
                    .custom_formatter(|v, _| format!("{v:.1} s"))
                    .step_by(0.1),
            );
            ui.add_space(4.0);

            ui.label(RichText::new("Seuil « appareil lent »").color(muted(ui)).small());
            ui.add(
                egui::Slider::new(&mut self.settings.slow_ms, 10.0..=300.0)
                    .custom_formatter(|v, _| format!("{v:.0} ms"))
                    .step_by(5.0),
            );
            ui.add_space(4.0);

            ui.checkbox(&mut self.settings.scan_on_start, "Scanner au démarrage");
            ui.checkbox(&mut self.settings.show_splash, "Écran de chargement (5 s min.)")
                .on_hover_text("Pris en compte au prochain lancement");
        });

        egui::CollapsingHeader::new("Colonnes du tableau").show(ui, |ui| {
            ui.checkbox(&mut self.settings.col_mac, "Adresse MAC");
            ui.checkbox(&mut self.settings.col_vendor, "Fabricant");
            ui.checkbox(&mut self.settings.col_type, "Type");
            ui.checkbox(&mut self.settings.col_host, "Nom d’hôte");
            ui.checkbox(&mut self.settings.col_latency, "Latence");
            ui.checkbox(&mut self.settings.col_label, "Étiquette");
        });

        egui::CollapsingHeader::new("Données").show(ui, |ui| {
            ui.add(egui::Label::new(config_dir().display().to_string()).selectable(true).wrap());
            ui.label(
                RichText::new(if has_vendor_database() {
                    "Base des fabricants : installée"
                } else {
                    "Base des fabricants : absente (bouton « Fabricants »)"
                })
                .color(muted(ui))
                .small(),
            );
            ui.add_space(4.0);
            ui.horizontal(|ui| {
                if ui.button("Ouvrir le dossier").clicked() {
                    open_folder(&config_dir());
                }
                if ui.button("Réinitialiser").clicked() {
                    self.settings = Settings::default();
                    self.view = View::List;
                }
            });
        });

        egui::CollapsingHeader::new("À propos").show(ui, |ui| {
            ui.label(format!(
                "ArpWise {} · Éditeur : {}",
                env!("CARGO_PKG_VERSION"),
                env!("CARGO_PKG_AUTHORS")
            ));
            if ui.button("Détails…").clicked() {
                self.show_about = true;
            }
        });

        self.settings_changed(ctx, &before);
    }

    /// Dialogs for the manual tools (Wake-on-LAN, ping/ports on any address)
    /// and the help windows.
    fn tool_dialogs(&mut self, ctx: &egui::Context) {
        let enter = |ui: &egui::Ui, response: &egui::Response| {
            response.lost_focus() && ui.input(|i| i.key_pressed(egui::Key::Enter))
        };

        // Wake-on-LAN by MAC address.
        if let Some(mac) = &mut self.wol_dialog {
            let mut send = false;
            let mut close = false;
            egui::Window::new("Wake-on-LAN")
                .collapsible(false)
                .resizable(false)
                .anchor(egui::Align2::CENTER_CENTER, [0.0, 0.0])
                .show(ctx, |ui| {
                    ui.label("Adresse MAC de la machine à réveiller :");
                    let response = ui.add(
                        egui::TextEdit::singleline(mac)
                            .hint_text("aa:bb:cc:dd:ee:ff")
                            .desired_width(280.0),
                    );
                    ui.add_space(4.0);
                    ui.horizontal(|ui| {
                        send = ui.button("Envoyer").clicked() || enter(ui, &response);
                        close = ui.button("Fermer").clicked();
                    });
                });
            let text = mac.clone();
            if send {
                self.status = match wake_on_lan(&text, Ipv4Addr::BROADCAST) {
                    Ok(()) => format!("Paquet Wake-on-LAN envoyé à {text}"),
                    Err(error) => error,
                };
            }
            if close {
                self.wol_dialog = None;
            }
        }

        // Ping / traceroute / ports on any address.
        if let Some(tool) = &mut self.host_dialog {
            let mut choice: Option<u8> = None;
            let mut close = false;
            egui::Window::new("Outils réseau")
                .collapsible(false)
                .resizable(false)
                .anchor(egui::Align2::CENTER_CENTER, [0.0, 0.0])
                .show(ctx, |ui| {
                    ui.label("Adresse IPv4 :");
                    ui.add(egui::TextEdit::singleline(&mut tool.ip).hint_text("192.168.1.10").desired_width(280.0));
                    ui.add_space(4.0);
                    ui.label("Ports (ex. 22,80,8000-8100) — vide = courants :");
                    ui.add(egui::TextEdit::singleline(&mut tool.ports).desired_width(280.0));
                    ui.add_space(6.0);
                    ui.horizontal(|ui| {
                        if ui.button("Ping").clicked() {
                            choice = Some(0);
                        }
                        if ui.button("Traceroute").clicked() {
                            choice = Some(1);
                        }
                        if ui.button("Ports").clicked() {
                            choice = Some(2);
                        }
                        close = ui.button("Fermer").clicked();
                    });
                });
            let (ip_text, ports_text) = (tool.ip.trim().to_string(), tool.ports.clone());

            if let Some(choice) = choice {
                match ip_text.parse::<Ipv4Addr>() {
                    Err(_) => self.status = format!("Adresse IPv4 invalide : {ip_text}"),
                    Ok(ip) => match choice {
                        0 => {
                            let (program, args) = ping_command(ip);
                            self.spawn_output(ctx, format!("Ping · {ip}"), move || run_command(program, &args));
                        }
                        1 => {
                            let (program, args) = traceroute_command(ip);
                            self.spawn_output(ctx, format!("Traceroute · {ip}"), move || {
                                run_command(program, &args)
                            });
                        }
                        _ => {
                            let ports = if ports_text.trim().is_empty() {
                                Ok(COMMON_PORTS.to_vec())
                            } else {
                                parse_ports(&ports_text)
                            };
                            match ports {
                                Ok(ports) => self.spawn_output(ctx, format!("Ports · {ip}"), move || {
                                    let open = scan_ports(ip, &ports, Duration::from_millis(500));
                                    Ok(format_ports(ip, &open, ports.len()))
                                }),
                                Err(error) => self.status = error,
                            }
                        }
                    },
                }
            }
            if close {
                self.host_dialog = None;
            }
        }

        egui::Window::new("Raccourcis clavier")
            .open(&mut self.show_shortcuts)
            .collapsible(false)
            .resizable(false)
            .anchor(egui::Align2::CENTER_CENTER, [0.0, 0.0])
            .show(ctx, |ui| {
                egui::Grid::new("shortcuts").num_columns(2).spacing([24.0, 8.0]).show(ui, |ui| {
                    for (keys, text) in [
                        ("F5  ou  Ctrl+R", "Rescanner le réseau"),
                        ("Ctrl+F", "Rechercher"),
                        ("Ctrl+E", "Exporter la liste"),
                        ("Clic droit", "Menu d’actions sur un appareil"),
                        ("Clic sur un titre", "Trier le tableau"),
                    ] {
                        ui.label(RichText::new(keys).strong());
                        ui.label(text);
                        ui.end_row();
                    }
                });
            });

        egui::Window::new("À propos d’ArpWise")
            .open(&mut self.show_about)
            .collapsible(false)
            .resizable(false)
            .anchor(egui::Align2::CENTER_CENTER, [0.0, 0.0])
            .show(ctx, |ui| {
                ui.vertical_centered(|ui| {
                    ui.add(
                        egui::Image::new(egui::load::SizedTexture::new(
                            self.logo.id(),
                            egui::vec2(270.0, 100.0),
                        ))
                        .corner_radius(egui::CornerRadius::same(10)),
                    );
                    ui.add_space(8.0);
                    ui.label(RichText::new("ArpWise").size(20.0).strong());
                    ui.label(format!("Version {}", env!("CARGO_PKG_VERSION")));
                    ui.add_space(6.0);
                    ui.label("Scanner réseau rapide, sans pilote,");
                    ui.label("pour Windows et Linux.");
                    ui.add_space(6.0);
                    ui.label(format!("Éditeur : {}", env!("CARGO_PKG_AUTHORS")));
                    ui.label(RichText::new("Licence GPL-3.0").color(muted(ui)).small());
                });
            });
    }

    fn dialogs(&mut self, ctx: &egui::Context) {
        if let Some(spec) = &mut self.ports_dialog {
            let mut launch = false;
            let mut cancel = false;
            egui::Window::new("Scanner les ports")
                .collapsible(false)
                .resizable(false)
                .anchor(egui::Align2::CENTER_CENTER, [0.0, 0.0])
                .show(ctx, |ui| {
                    ui.label("Ports (ex. 22,80,8000-8100) — vide = ports courants :");
                    let response = ui.add(egui::TextEdit::singleline(spec).desired_width(280.0));
                    ui.horizontal(|ui| {
                        launch = ui.button("Lancer").clicked()
                            || (response.lost_focus() && ui.input(|i| i.key_pressed(egui::Key::Enter)));
                        cancel = ui.button("Annuler").clicked();
                    });
                });

            if cancel {
                self.ports_dialog = None;
            } else if launch {
                let spec = std::mem::take(spec);
                let parsed = if spec.trim().is_empty() {
                    Ok(COMMON_PORTS.to_vec())
                } else {
                    parse_ports(&spec)
                };
                match (parsed, self.selected().map(|r| r.device.ip)) {
                    (Ok(ports), Some(ip)) => {
                        self.ports_dialog = None;
                        self.spawn_output(ctx, format!("Ports · {ip}"), move || {
                            let open = scan_ports(ip, &ports, Duration::from_millis(500));
                            Ok(format_ports(ip, &open, ports.len()))
                        });
                    }
                    (Err(error), _) => {
                        self.status = error;
                        self.ports_dialog = Some(spec);
                    }
                    (_, None) => self.ports_dialog = None,
                }
            }
        }

        let mut close = false;
        if let Some((title, text)) = &self.output {
            egui::Window::new(title.as_str())
                .collapsible(false)
                .default_size([560.0, 380.0])
                .show(ctx, |ui| {
                    egui::ScrollArea::vertical().max_height(300.0).show(ui, |ui| {
                        ui.add(egui::Label::new(RichText::new(text).monospace()).selectable(true));
                    });
                    ui.add_space(6.0);
                    close = ui.button("Fermer").clicked();
                });
        }
        if close {
            self.output = None;
        }
    }
}

fn type_color(kind: DeviceType) -> Color32 {
    match kind {
        DeviceType::Router => accent(),
        DeviceType::NetworkGear => Color32::from_rgb(0x2d, 0xb7, 0xb0),
        DeviceType::Computer => Color32::from_rgb(0x6c, 0xa6, 0xe8),
        DeviceType::Mobile => Color32::from_rgb(0xb0, 0x8a, 0xf0),
        DeviceType::Printer => Color32::from_rgb(0xe8, 0x93, 0x4a),
        DeviceType::Media => Color32::from_rgb(0xe8, 0x6c, 0xa8),
        DeviceType::Iot => GOOD,
        DeviceType::Unknown => Color32::from_gray(0x8a),
    }
}

/// A small latency graph for one device.
fn sparkline(ui: &mut egui::Ui, series: &[f64]) {
    let min = series.iter().cloned().fold(f64::MAX, f64::min);
    let max = series.iter().cloned().fold(f64::MIN, f64::max);
    let avg = series.iter().sum::<f64>() / series.len() as f64;

    ui.label(RichText::new("Latence (cette session)").color(muted(ui)).small());
    let (rect, _) = ui.allocate_exact_size(egui::vec2(ui.available_width(), 46.0), egui::Sense::hover());
    let painter = ui.painter_at(rect);
    painter.rect_filled(rect, 0.0, ui.visuals().extreme_bg_color);

    let span = (max - min).max(1.0);
    let points: Vec<egui::Pos2> = series
        .iter()
        .enumerate()
        .map(|(i, v)| {
            let x = rect.left() + 4.0 + (rect.width() - 8.0) * i as f32 / (series.len() - 1) as f32;
            let y = rect.bottom() - 4.0 - (rect.height() - 8.0) * ((v - min) / span) as f32;
            egui::pos2(x, y)
        })
        .collect();
    painter.add(egui::Shape::line(points, egui::Stroke::new(1.5, accent())));
    ui.label(
        RichText::new(format!("min {min:.0} · moy {avg:.0} · max {max:.0} ms · {} mesures", series.len()))
            .color(muted(ui))
            .small(),
    );
    ui.add_space(6.0);
}

/// Decode the embedded publisher logo; returns the texture and its
/// background colour so the splash screen blends in seamlessly.
fn load_logo(ctx: &egui::Context) -> (egui::TextureHandle, Color32) {
    let bytes = include_bytes!("../../assets/qoats-logo.jpg");
    let rgba = image::load_from_memory(bytes)
        .expect("valid embedded logo")
        .to_rgba8();
    let (w, h) = (rgba.width() as usize, rgba.height() as usize);
    let corner = rgba.get_pixel(2, 2);
    let background = Color32::from_rgb(corner[0], corner[1], corner[2]);
    let color_image = egui::ColorImage::from_rgba_unmultiplied([w, h], rgba.as_raw());
    let texture = ctx.load_texture("qoats-logo", color_image, egui::TextureOptions::LINEAR);
    (texture, background)
}

/// Put the window in the middle of the screen it is on.
fn center_window(ctx: &egui::Context) {
    if let Some(command) = egui::ViewportCommand::center_on_screen(ctx) {
        ctx.send_viewport_cmd(command);
    }
}

fn muted(ui: &egui::Ui) -> Color32 {
    ui.visuals().weak_text_color()
}

/// Green below 40 % of the "slow" threshold, orange below 160 %, red above.
fn latency_color(latency: Option<f64>, slow: f64) -> Color32 {
    match latency {
        None => Color32::from_gray(0x80),
        Some(ms) if ms < slow * 0.4 => GOOD,
        Some(ms) if ms < slow * 1.6 => WARN,
        Some(_) => BAD,
    }
}

fn open_folder(path: &std::path::Path) {
    let program = if cfg!(windows) { "explorer" } else { "xdg-open" };
    let _ = std::process::Command::new(program).arg(path).spawn();
}

/// Rounded card used for the main panels.
fn panel_frame(ui: &egui::Ui) -> egui::Frame {
    let dark = ui.visuals().dark_mode;
    egui::Frame::new()
        .fill(if dark { PANEL } else { Color32::WHITE })
        .corner_radius(egui::CornerRadius::same(14))
        .stroke(egui::Stroke::new(
            1.0,
            if dark { Color32::from_rgb(0x22, 0x2e, 0x3d) } else { Color32::from_rgb(0xd8, 0xdf, 0xe9) },
        ))
        .inner_margin(egui::Margin::same(14))
}

/// `2026-11-18T14:03:09` -> `18/11/2026 14:03`.
fn pretty_time(stamp: &str) -> String {
    let Some((date, time)) = stamp.split_once('T') else {
        return "—".into();
    };
    let parts: Vec<&str> = date.split('-').collect();
    match parts.as_slice() {
        [y, m, d] => format!("{d}/{m}/{y} {}", time.get(..5).unwrap_or(time)),
        _ => stamp.into(),
    }
}

fn field(ui: &mut egui::Ui, name: &str, value: &str) {
    ui.label(RichText::new(name).color(muted(ui)).small());
    ui.add(egui::Label::new(if value.is_empty() { "—" } else { value }).selectable(true));
    ui.add_space(6.0);
}

fn card(ui: &mut egui::Ui, title: &str, value: &str, color: Color32) {
    egui::Frame::new()
        .fill(if ui.visuals().dark_mode { CARD } else { Color32::from_rgb(0xf0, 0xf3, 0xf8) })
        .corner_radius(egui::CornerRadius::same(12))
        .stroke(egui::Stroke::new(1.0, ui.visuals().widgets.noninteractive.bg_stroke.color))
        .inner_margin(egui::Margin::symmetric(16, 10))
        .show(ui, |ui| {
            ui.vertical(|ui| {
                ui.set_min_width(110.0);
                ui.label(RichText::new(title).color(muted(ui)).small());
                ui.label(RichText::new(value).size(22.0).strong().color(color));
            });
        });
}

fn apply_style(ctx: &egui::Context, dark: bool) {
    let acc = accent();
    let mut visuals = if dark { egui::Visuals::dark() } else { egui::Visuals::light() };

    if dark {
        visuals.panel_fill = BG;
        visuals.window_fill = PANEL;
        visuals.extreme_bg_color = Color32::from_rgb(0x0a, 0x11, 0x19);
        visuals.faint_bg_color = Color32::from_rgb(0x15, 0x1e, 0x29);
        let soft = Color32::from_rgb(0x1a, 0x25, 0x32);
        visuals.widgets.inactive.bg_fill = soft;
        visuals.widgets.inactive.weak_bg_fill = soft;
        visuals.widgets.inactive.bg_stroke = egui::Stroke::new(1.0, Color32::from_rgb(0x2a, 0x37, 0x48));
        visuals.widgets.noninteractive.bg_stroke = egui::Stroke::new(1.0, Color32::from_rgb(0x22, 0x2e, 0x3d));
        let hover = Color32::from_rgb(0x23, 0x31, 0x42);
        visuals.widgets.hovered.bg_fill = hover;
        visuals.widgets.hovered.weak_bg_fill = hover;
    } else {
        visuals.panel_fill = Color32::from_rgb(0xea, 0xee, 0xf4);
        visuals.window_fill = Color32::WHITE;
        visuals.extreme_bg_color = Color32::WHITE;
        visuals.faint_bg_color = Color32::from_rgb(0xf3, 0xf6, 0xfa);
        visuals.widgets.inactive.bg_stroke = egui::Stroke::new(1.0, Color32::from_rgb(0xc4, 0xcd, 0xda));
        visuals.widgets.noninteractive.bg_stroke = egui::Stroke::new(1.0, Color32::from_rgb(0xd8, 0xdf, 0xe9));
    }

    visuals.selection.bg_fill = acc.gamma_multiply(if dark { 0.45 } else { 0.30 });
    visuals.selection.stroke = egui::Stroke::new(1.0, acc);
    visuals.hyperlink_color = acc;

    for widget in [
        &mut visuals.widgets.noninteractive,
        &mut visuals.widgets.inactive,
        &mut visuals.widgets.hovered,
        &mut visuals.widgets.active,
        &mut visuals.widgets.open,
    ] {
        widget.corner_radius = egui::CornerRadius::same(8);
    }
    visuals.window_corner_radius = egui::CornerRadius::same(14);
    visuals.menu_corner_radius = egui::CornerRadius::same(10);
    ctx.set_visuals(visuals);

    ctx.all_styles_mut(|style| {
        style.spacing.item_spacing = egui::vec2(8.0, 7.0);
        style.spacing.button_padding = egui::vec2(12.0, 6.0);
        style.spacing.interact_size.y = 30.0;
        style.spacing.window_margin = egui::Margin::same(16);
    });
}

impl eframe::App for App {
    fn ui(&mut self, ui: &mut egui::Ui, _frame: &mut eframe::Frame) {
        let ctx = ui.ctx().clone();
        self.poll_messages();

        // Centre the window on screen as soon as it exists.
        if !self.splash_centered {
            self.splash_centered = true;
            center_window(&ctx);
        }

        // Loading screen: a small window the size of the logo, shown at least
        // SPLASH_MIN seconds and until the first scan is done (SPLASH_MAX cap).
        // Then the real window opens, centred on screen.
        if !self.splash_done {
            let t = self.splash_start.elapsed().as_secs_f32();

            if self.splash_closing == 0 && t >= SPLASH_MIN && (!self.scanning || t >= SPLASH_MAX) {
                ctx.send_viewport_cmd(egui::ViewportCommand::Decorations(true));
                ctx.send_viewport_cmd(egui::ViewportCommand::Resizable(true));
                ctx.send_viewport_cmd(egui::ViewportCommand::MinInnerSize(egui::vec2(1040.0, 600.0)));
                ctx.send_viewport_cmd(egui::ViewportCommand::InnerSize(egui::vec2(1280.0, 760.0)));
                self.splash_closing = 14;
            }

            if self.splash_closing > 0 {
                // Blank frames while the window grows. Centring has to wait
                // until it has its new size, so it is done a few frames later
                // (and once more to be safe).
                self.splash_closing -= 1;
                if self.splash_closing == 8 || self.splash_closing == 3 {
                    center_window(&ctx);
                }
                if self.splash_closing == 0 {
                    self.splash_done = true;
                    self.last_scan = Instant::now();
                    ctx.set_zoom_factor(self.settings.ui_scale);
                }
                egui::CentralPanel::default()
                    .frame(egui::Frame::new().fill(self.splash_bg))
                    .show(ui, |_| {});
                ctx.request_repaint_after(Duration::from_millis(25));
                return;
            }

            self.splash(ui, t);
            ctx.request_repaint_after(Duration::from_millis(33));
            return;
        }

        // Keyboard shortcuts.
        let (rescan, find, export) = ctx.input(|i| {
            (
                i.key_pressed(egui::Key::F5) || (i.modifiers.command && i.key_pressed(egui::Key::R)),
                i.modifiers.command && i.key_pressed(egui::Key::F),
                i.modifiers.command && i.key_pressed(egui::Key::E),
            )
        });
        if rescan {
            self.start_scan(&ctx);
        }
        if find {
            ctx.memory_mut(|m| m.request_focus(self.search_id));
        }
        if export {
            self.export();
        }

        // Automatic rescan.
        if self.settings.auto_scan_secs > 0 {
            let interval = Duration::from_secs(self.settings.auto_scan_secs);
            if !self.scanning && self.last_scan.elapsed() >= interval {
                self.start_scan(&ctx);
            }
            ctx.request_repaint_after(Duration::from_secs(1));
        }

        let bg = ui.visuals().panel_fill;

        egui::Panel::top("menu")
            .frame(egui::Frame::new().fill(bg).inner_margin(egui::Margin::symmetric(10, 4)))
            .show(ui, |ui| self.menu_bar(ui, &ctx));

        egui::Panel::top("toolbar")
            .frame(egui::Frame::new().fill(bg).inner_margin(egui::Margin::symmetric(14, 8)))
            .show(ui, |ui| self.top_bar(ui, &ctx));

        egui::Panel::bottom("status")
            .frame(egui::Frame::new().fill(bg).inner_margin(egui::Margin::symmetric(16, 6)))
            .show(ui, |ui| {
                ui.label(RichText::new(&self.status).color(muted(ui)).small());
            });

        egui::Panel::right("inspector")
            .exact_size(372.0)
            .resizable(false)
            .frame(egui::Frame::new().fill(bg).inner_margin(egui::Margin {
                left: 0,
                right: 12,
                top: 4,
                bottom: 4,
            }))
            .show(ui, |ui| {
                panel_frame(ui).show(ui, |ui| {
                    ui.set_min_size(ui.available_size());
                    self.side_panel(ui, &ctx);
                });
            });

        egui::CentralPanel::default()
            .frame(egui::Frame::new().fill(bg).inner_margin(egui::Margin {
                left: 12,
                right: 12,
                top: 4,
                bottom: 4,
            }))
            .show(ui, |ui| {
                panel_frame(ui).show(ui, |ui| {
                    ui.set_min_size(ui.available_size());
                    self.table(ui, &ctx);
                });
            });

        self.dialogs(&ctx);        self.dialogs(&ctx);
        self.tool_dialogs(&ctx);

        // Remember the chosen view.
        let map_view = self.view == View::Map;
        if map_view != self.settings.map_view {
            self.settings.map_view = map_view;
            save_settings(&self.settings);
        }
    }
}

fn main() -> eframe::Result {
    let settings = load_settings();
    let mut viewport = egui::ViewportBuilder::default()
        .with_title("ArpWise")
        .with_icon(
            eframe::icon_data::from_png_bytes(include_bytes!("../../assets/icon.png"))
                .expect("valid embedded icon"),
        );
    viewport = if settings.show_splash {
        // Small borderless window the size of the logo; it grows afterwards.
        viewport
            .with_decorations(false)
            .with_resizable(false)
            .with_inner_size([450.0, 166.0])
    } else {
        viewport
            .with_inner_size([1280.0, 760.0])
            .with_min_inner_size([1040.0, 600.0])
    };
    if settings.always_on_top {
        viewport = viewport.with_always_on_top();
    }
    let options = eframe::NativeOptions { viewport, ..Default::default() };
    eframe::run_native("ArpWise", options, Box::new(|cc| Ok(Box::new(App::new(cc)))))
}
