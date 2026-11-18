#![cfg_attr(windows, windows_subsystem = "windows")]

use std::collections::{HashMap, HashSet};
use std::net::Ipv4Addr;
use std::sync::atomic::{AtomicUsize, Ordering};
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
const SPLASH_MAX: f32 = 20.0;

const BG: Color32 = Color32::from_rgb(0x0d, 0x13, 0x1b);
const PANEL: Color32 = Color32::from_rgb(0x11, 0x18, 0x21);
const CARD: Color32 = Color32::from_rgb(0x15, 0x1f, 0x2b);
const BORDER: Color32 = Color32::from_rgb(0x2c, 0x3a, 0x4b);
const ACCENT: Color32 = Color32::from_rgb(0x2f, 0x7d, 0xf4);
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
        apply_style(&cc.egui_ctx, settings.dark_theme);
        let (logo, splash_bg) = load_logo(&cc.egui_ctx);
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
            splash_start: Instant::now(),
            splash_done: false,
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
        app.start_scan(&cc.egui_ctx);
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
        std::thread::spawn(move || {
            let report = {
                let ctx = ctx.clone();
                move |finished: usize, _total: usize| {
                    done.store(finished, Ordering::Relaxed);
                    ctx.request_repaint();
                }
            };
            let result = scan_network(&network, 1.0, Some(&report)).map(|mut devices| {
                ping_all(&mut devices, 1.0);
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
                    Filter::Slow => row.online && d.latency_ms.is_some_and(|ms| ms >= 50.0),
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
        let devices = self.online_devices();
        if devices.is_empty() {
            self.status = "Aucun appareil à exporter.".into();
            return;
        }
        let Some(path) = rfd::FileDialog::new()
            .set_file_name("arpwise.csv")
            .add_filter("CSV", &["csv"])
            .add_filter("JSON", &["json"])
            .save_file()
        else {
            return;
        };
        self.status = match export_devices(&devices, &path, &self.labels) {
            Ok(()) => format!("{} appareil(s) exporté(s) : {}", devices.len(), path.display()),
            Err(error) => error,
        };
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
            .fill(ACCENT)
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
            card(ui, "Latence moyenne", &average, ACCENT);
        });
    }

    fn table(&mut self, ui: &mut egui::Ui, ctx: &egui::Context) {
        self.stats(ui);
        ui.add_space(8.0);

        ui.horizontal(|ui| {
            for (filter, text) in [
                (Filter::All, "Tous"),
                (Filter::New, "Nouveaux"),
                (Filter::Slow, "Lents (≥ 50 ms)"),
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

        let headers = [
            (SortBy::Ip, "Adresse IP"),
            (SortBy::Mac, "Adresse MAC"),
            (SortBy::Vendor, "Fabricant"),
            (SortBy::Type, "Type"),
            (SortBy::Host, "Nom d’hôte"),
            (SortBy::Latency, "Latence"),
            (SortBy::Label, "Étiquette"),
            (SortBy::Status, ""),
        ];

        TableBuilder::new(ui)
            .striped(true)
            .sense(egui::Sense::click())
            .column(Column::auto().at_least(110.0))
            .column(Column::auto().at_least(140.0))
            .column(Column::initial(160.0).at_least(80.0).clip(true))
            .column(Column::auto().at_least(100.0))
            .column(Column::initial(150.0).at_least(80.0).clip(true))
            .column(Column::auto().at_least(80.0))
            .column(Column::remainder().at_least(80.0).clip(true))
            .column(Column::auto().at_least(90.0))
            .header(26.0, |mut header| {
                for (column, title) in headers {
                    header.col(|ui| {
                        let arrow = if self.sort == column {
                            if self.sort_desc { " ▼" } else { " ▲" }
                        } else {
                            ""
                        };
                        let text = RichText::new(format!("{title}{arrow}")).strong().color(muted(ui));
                        if ui.add(egui::Label::new(text).sense(egui::Sense::click())).clicked() {
                            sort_request = Some(column);
                        }
                    });
                }
            })
            .body(|body| {
                body.rows(28.0, visible.len(), |mut row| {
                    let item = &self.rows[visible[row.index()]];
                    let device = &item.device;
                    row.set_selected(self.selected_mac.as_deref() == Some(device.mac.as_str()));

                    let dim = |ui: &egui::Ui, text: &str| {
                        let color = if item.online { ui.visuals().text_color() } else { muted(ui) };
                        RichText::new(text).color(color)
                    };

                    row.col(|ui| {
                        ui.label(dim(ui, &device.ip.to_string()));
                    });
                    row.col(|ui| {
                        ui.label(dim(ui, &device.mac).monospace());
                    });
                    row.col(|ui| {
                        ui.label(dim(ui, &device.vendor));
                    });
                    row.col(|ui| {
                        let color = if item.online { type_color(item.kind) } else { muted(ui) };
                        ui.label(RichText::new(item.kind.label()).color(color));
                    });
                    row.col(|ui| {
                        let host = if device.hostname.is_empty() { "—" } else { &device.hostname };
                        ui.label(dim(ui, host));
                    });
                    row.col(|ui| {
                        if item.online {
                            ui.horizontal(|ui| {
                                ui.spacing_mut().item_spacing.x = 4.0;
                                ui.label(RichText::new("●").color(latency_color(device.latency_ms)));
                                ui.label(device.latency_ms.map_or("—".to_string(), |ms| format!("{ms:.0} ms")));
                            });
                        } else {
                            ui.label(RichText::new("hors ligne").color(muted(ui)));
                        }
                    });
                    row.col(|ui| {
                        ui.label(get_label(&self.labels, &device.mac));
                    });
                    row.col(|ui| {
                        if self.is_new(device) {
                            ui.label(RichText::new("NOUVEAU").color(WARN).strong());
                        }
                    });

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
                (true, Some(ms)) if ms < 20.0 => 0.38,
                (true, Some(ms)) if ms < 80.0 => 0.68,
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
        painter.circle_filled(center, 22.0, ACCENT);
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
            let color = if row.online { latency_color(row.device.latency_ms) } else { Color32::from_gray(0x6a) };

            if pointer.is_some_and(|p| p.distance(node.pos) < 17.0) {
                hovered = Some(node.index);
            }
            if selected || hovered == Some(node.index) {
                painter.circle_stroke(node.pos, 20.0, egui::Stroke::new(2.0, ACCENT));
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
            (GOOD, "< 20 ms"),
            (WARN, "< 80 ms"),
            (BAD, "≥ 80 ms"),
            (Color32::from_gray(0x6a), "hors ligne"),
        ];
        for (n, (color, text)) in legend.iter().enumerate() {
            let y = rect.bottom() - 14.0 - 16.0 * (legend.len() - 1 - n) as f32;
            painter.circle_filled(egui::pos2(rect.left() + 14.0, y), 5.0, *color);
            painter.text(
                egui::pos2(rect.left() + 26.0, y),
                egui::Align2::LEFT_CENTER,
                *text,
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
        ui.label(RichText::new("Réglages").size(14.0).strong());
        ui.add_space(8.0);

        let before = self.settings.clone();

        ui.label(RichText::new("Thème").color(muted(ui)).small());
        ui.horizontal(|ui| {
            ui.selectable_value(&mut self.settings.dark_theme, true, "Sombre");
            ui.selectable_value(&mut self.settings.dark_theme, false, "Clair");
        });
        ui.add_space(8.0);

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
        ui.add_space(8.0);

        ui.checkbox(&mut self.settings.show_offline, "Afficher les appareils hors ligne");

        ui.add_space(12.0);
        ui.label(RichText::new("À propos").color(muted(ui)).small());
        ui.label(format!(
            "ArpWise {} · Éditeur : {}",
            env!("CARGO_PKG_VERSION"),
            env!("CARGO_PKG_AUTHORS")
        ));
        ui.add_space(12.0);
        ui.label(RichText::new("Données").color(muted(ui)).small());
        ui.add(egui::Label::new(config_dir().display().to_string()).selectable(true).wrap());
        ui.add_space(6.0);
        ui.label(
            RichText::new(if has_vendor_database() {
                "Base des fabricants : installée"
            } else {
                "Base des fabricants : absente (bouton « Fabricants »)"
            })
            .color(muted(ui))
            .small(),
        );

        if self.settings.dark_theme != before.dark_theme {
            apply_style(ctx, self.settings.dark_theme);
        }
        if self.settings.auto_scan_secs != before.auto_scan_secs
            || self.settings.show_offline != before.show_offline
            || self.settings.dark_theme != before.dark_theme
        {
            save_settings(&self.settings);
        }
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
        DeviceType::Router => ACCENT,
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
    painter.add(egui::Shape::line(points, egui::Stroke::new(1.5, ACCENT)));
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

fn muted(ui: &egui::Ui) -> Color32 {
    ui.visuals().weak_text_color()
}

fn latency_color(latency: Option<f64>) -> Color32 {
    match latency {
        None => Color32::from_gray(0x80),
        Some(ms) if ms < 20.0 => GOOD,
        Some(ms) if ms < 80.0 => WARN,
        Some(_) => BAD,
    }
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
        .fill(if ui.visuals().dark_mode { CARD } else { Color32::from_rgb(0xf0, 0xf3, 0xf7) })
        .stroke(egui::Stroke::new(1.0, ui.visuals().widgets.noninteractive.bg_stroke.color))
        .inner_margin(egui::Margin::symmetric(14, 8))
        .show(ui, |ui| {
            ui.vertical(|ui| {
                ui.set_min_width(110.0);
                ui.label(RichText::new(title).color(muted(ui)).small());
                ui.label(RichText::new(value).size(22.0).strong().color(color));
            });
        });
}

fn apply_style(ctx: &egui::Context, dark: bool) {
    let mut visuals = if dark { egui::Visuals::dark() } else { egui::Visuals::light() };
    if dark {
        visuals.panel_fill = PANEL;
        visuals.window_fill = BG;
        visuals.extreme_bg_color = Color32::from_rgb(0x0a, 0x11, 0x19);
        visuals.faint_bg_color = Color32::from_rgb(0x13, 0x1c, 0x27);
        visuals.selection.bg_fill = Color32::from_rgb(0x1f, 0x51, 0x85);
        visuals.widgets.inactive.bg_fill = Color32::from_rgb(0x17, 0x21, 0x2d);
        visuals.widgets.inactive.weak_bg_fill = Color32::from_rgb(0x17, 0x21, 0x2d);
        visuals.widgets.inactive.bg_stroke = egui::Stroke::new(1.0, BORDER);
    } else {
        visuals.selection.bg_fill = Color32::from_rgb(0xbf, 0xd8, 0xfb);
    }
    visuals.hyperlink_color = ACCENT;
    for widget in [
        &mut visuals.widgets.noninteractive,
        &mut visuals.widgets.inactive,
        &mut visuals.widgets.hovered,
        &mut visuals.widgets.active,
        &mut visuals.widgets.open,
    ] {
        widget.corner_radius = egui::CornerRadius::ZERO;
    }
    visuals.window_corner_radius = egui::CornerRadius::ZERO;
    ctx.set_visuals(visuals);
}

impl eframe::App for App {
    fn ui(&mut self, ui: &mut egui::Ui, _frame: &mut eframe::Frame) {
        let ctx = ui.ctx().clone();
        self.poll_messages();

        // Loading screen: a small window the size of the logo, shown at least
        // SPLASH_MIN seconds and until the first scan is done (SPLASH_MAX cap).
        // Then the real window opens.
        if !self.splash_done {
            let t = self.splash_start.elapsed().as_secs_f32();

            if !self.splash_centered {
                self.splash_centered = true;
                if let Some(command) = egui::ViewportCommand::center_on_screen(&ctx) {
                    ctx.send_viewport_cmd(command);
                }
            }

            if self.splash_closing == 0 && t >= SPLASH_MIN && (!self.scanning || t >= SPLASH_MAX) {
                ctx.send_viewport_cmd(egui::ViewportCommand::Decorations(true));
                ctx.send_viewport_cmd(egui::ViewportCommand::Resizable(true));
                ctx.send_viewport_cmd(egui::ViewportCommand::MinInnerSize(egui::vec2(1040.0, 600.0)));
                ctx.send_viewport_cmd(egui::ViewportCommand::InnerSize(egui::vec2(1280.0, 760.0)));
                if let Some(command) = egui::ViewportCommand::center_on_screen(&ctx) {
                    ctx.send_viewport_cmd(command);
                }
                self.splash_closing = 4;
            }

            if self.splash_closing > 0 {
                // Blank frames while the window changes size.
                self.splash_closing -= 1;
                if self.splash_closing == 0 {
                    self.splash_done = true;
                    self.last_scan = Instant::now();
                }
                egui::CentralPanel::default()
                    .frame(egui::Frame::new().fill(self.splash_bg))
                    .show(ui, |_| {});
                ctx.request_repaint();
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

        egui::Panel::top("top").show(ui, |ui| {
            ui.add_space(6.0);
            self.top_bar(ui, &ctx);
            ui.add_space(6.0);
        });

        egui::Panel::bottom("status").show(ui, |ui| {
            ui.label(RichText::new(&self.status).color(muted(ui)));
        });

        egui::Panel::right("inspector")
            .exact_size(330.0)
            .resizable(false)
            .show(ui, |ui| self.side_panel(ui, &ctx));

        egui::CentralPanel::default().show(ui, |ui| self.table(ui, &ctx));

        self.dialogs(&ctx);

        // Remember the chosen view.
        let map_view = self.view == View::Map;
        if map_view != self.settings.map_view {
            self.settings.map_view = map_view;
            save_settings(&self.settings);
        }
    }
}

fn main() -> eframe::Result {
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_title("ArpWise")
            .with_icon(
                eframe::icon_data::from_png_bytes(include_bytes!("../../assets/icon.png"))
                    .expect("valid embedded icon"),
            )
            .with_decorations(false)
            .with_resizable(false)
            .with_inner_size([450.0, 166.0]),
        ..Default::default()
    };
    eframe::run_native("ArpWise", options, Box::new(|cc| Ok(Box::new(App::new(cc)))))
}
