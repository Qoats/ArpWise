#![cfg_attr(windows, windows_subsystem = "windows")]

use std::collections::HashSet;
use std::net::Ipv4Addr;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::mpsc::{channel, Receiver, Sender};
use std::sync::Arc;
use std::time::Duration;

use eframe::egui::{self, Color32, RichText};
use egui_extras::{Column, TableBuilder};
use netscanpy::{
    config::normalize_mac,
    export::export_devices,
    history::record_scan,
    labels::{get_label, load_labels, save_labels, Labels},
    netinfo::{fetch_public_info, PublicInfo},
    network::{local_network_info, parse_network, LocalInfo},
    scanner::scan_network,
    tools::{
        COMMON_PORTS, format_ports, ping_all, ping_command, parse_ports, run_command, scan_ports,
        traceroute_command, wake_on_lan,
    },
    vendors::{has_vendor_database, update_vendors},
    Device,
};

const BG: Color32 = Color32::from_rgb(0x0d, 0x13, 0x1b);
const PANEL: Color32 = Color32::from_rgb(0x11, 0x18, 0x21);
const BORDER: Color32 = Color32::from_rgb(0x2c, 0x3a, 0x4b);
const ACCENT: Color32 = Color32::from_rgb(0x2f, 0x7d, 0xf4);
const MUTED: Color32 = Color32::from_rgb(0x97, 0xa6, 0xb8);
const WARN: Color32 = Color32::from_rgb(0xf5, 0xb9, 0x42);

enum Msg {
    Scan(Result<(Vec<Device>, HashSet<String>), String>),
    Public(Result<PublicInfo, String>),
    Vendors(Result<usize, String>),
    Output { title: String, result: Result<String, String> },
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum Column_ {
    Ip,
    Mac,
    Vendor,
    Host,
    Latency,
    Label,
    Status,
}

#[derive(PartialEq, Eq, Clone, Copy)]
enum Tab {
    Device,
    Network,
}

struct App {
    tx: Sender<Msg>,
    rx: Receiver<Msg>,

    network_input: String,
    local: Option<LocalInfo>,
    public: Option<Result<PublicInfo, String>>,

    devices: Vec<Device>,
    new_macs: HashSet<String>,
    labels: Labels,
    selected_mac: Option<String>,
    label_edit: String,

    search: String,
    sort: Column_,
    sort_desc: bool,
    tab: Tab,

    scanning: bool,
    busy: bool,
    done: Arc<AtomicUsize>,
    total: Arc<AtomicUsize>,
    status: String,

    ports_dialog: Option<String>,
    output: Option<(String, String)>,
}

impl App {
    fn new(cc: &eframe::CreationContext<'_>) -> Self {
        apply_style(&cc.egui_ctx);
        let (tx, rx) = channel();
        let local = local_network_info();
        let mut app = Self {
            tx,
            rx,
            network_input: local.as_ref().map(|l| l.network.to_string()).unwrap_or_default(),
            local,
            public: None,
            devices: Vec::new(),
            new_macs: HashSet::new(),
            labels: load_labels(),
            selected_mac: None,
            label_edit: String::new(),
            search: String::new(),
            sort: Column_::Ip,
            sort_desc: false,
            tab: Tab::Device,
            scanning: false,
            busy: false,
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
        self.devices.clear();
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
                let (new_macs, _) = record_scan(&devices);
                (devices, new_macs)
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
                Msg::Scan(Ok((devices, new_macs))) => {
                    self.scanning = false;
                    self.status = format!("{} appareil(s) détecté(s) · {}", devices.len(), self.network_input);
                    if !new_macs.is_empty() {
                        self.status += &format!(" · {} nouveau(x)", new_macs.len());
                    }
                    if !has_vendor_database() {
                        self.status += " · cliquez sur « Fabricants » pour identifier les marques";
                    }
                    self.devices = devices;
                    self.new_macs = new_macs;
                    self.select_first_if_needed();
                }
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

    fn select_first_if_needed(&mut self) {
        let still_there = self
            .selected_mac
            .as_ref()
            .is_some_and(|mac| self.devices.iter().any(|d| &d.mac == mac));
        if !still_there {
            self.selected_mac = self.devices.first().map(|d| d.mac.clone());
            self.sync_label_edit();
        }
    }

    fn sync_label_edit(&mut self) {
        self.label_edit = self
            .selected_mac
            .as_deref()
            .map(|mac| get_label(&self.labels, mac).to_string())
            .unwrap_or_default();
    }

    fn selected(&self) -> Option<&Device> {
        let mac = self.selected_mac.as_ref()?;
        self.devices.iter().find(|d| &d.mac == mac)
    }

    /// Indices of devices matching the search, in display order.
    fn visible(&self) -> Vec<usize> {
        let query = self.search.trim().to_lowercase();
        let mut indices: Vec<usize> = (0..self.devices.len())
            .filter(|&i| {
                let d = &self.devices[i];
                query.is_empty()
                    || format!(
                        "{} {} {} {} {}",
                        d.ip,
                        d.mac,
                        d.vendor,
                        d.hostname,
                        get_label(&self.labels, &d.mac)
                    )
                    .to_lowercase()
                    .contains(&query)
            })
            .collect();

        indices.sort_by(|&a, &b| {
            let (da, db) = (&self.devices[a], &self.devices[b]);
            let ordering = match self.sort {
                Column_::Ip => u32::from(da.ip).cmp(&u32::from(db.ip)),
                Column_::Mac => da.mac.cmp(&db.mac),
                Column_::Vendor => da.vendor.to_lowercase().cmp(&db.vendor.to_lowercase()),
                Column_::Host => da.hostname.to_lowercase().cmp(&db.hostname.to_lowercase()),
                Column_::Latency => da
                    .latency_ms
                    .unwrap_or(f64::MAX)
                    .total_cmp(&db.latency_ms.unwrap_or(f64::MAX)),
                Column_::Label => get_label(&self.labels, &da.mac)
                    .to_lowercase()
                    .cmp(&get_label(&self.labels, &db.mac).to_lowercase()),
                Column_::Status => self
                    .is_new(db)
                    .cmp(&self.is_new(da)),
            };
            if self.sort_desc { ordering.reverse() } else { ordering }
        });
        indices
    }

    fn is_new(&self, device: &Device) -> bool {
        self.new_macs.contains(&normalize_mac(&device.mac))
    }

    fn export(&mut self) {
        if self.devices.is_empty() {
            self.status = "Aucun appareil à exporter.".into();
            return;
        }
        let Some(path) = rfd::FileDialog::new()
            .set_file_name("netscanpy.csv")
            .add_filter("CSV", &["csv"])
            .add_filter("JSON", &["json"])
            .save_file()
        else {
            return;
        };
        self.status = match export_devices(&self.devices, &path, &self.labels) {
            Ok(()) => format!("{} appareil(s) exporté(s) : {}", self.devices.len(), path.display()),
            Err(error) => error,
        };
    }

    // ---- UI ----------------------------------------------------------

    fn top_bar(&mut self, ui: &mut egui::Ui, ctx: &egui::Context) {
        ui.horizontal(|ui| {
            ui.add_space(6.0);
            ui.label(RichText::new("NetScanPy").size(18.0).strong().color(Color32::WHITE));
            ui.add_space(16.0);
            ui.label(RichText::new("Réseau").color(MUTED));
            ui.add(
                egui::TextEdit::singleline(&mut self.network_input)
                    .hint_text("Détection automatique du réseau…")
                    .desired_width(220.0),
            );

            let scan = egui::Button::new(
                RichText::new(if self.scanning { "Analyse…" } else { "Scanner" }).strong(),
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

    fn table(&mut self, ui: &mut egui::Ui) {
        ui.horizontal(|ui| {
            ui.label(RichText::new("Inventaire réseau").size(14.0).strong());
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                ui.add(
                    egui::TextEdit::singleline(&mut self.search)
                        .hint_text("Rechercher IP, MAC, hôte…")
                        .desired_width(260.0),
                );
            });
        });
        ui.add_space(6.0);

        if self.devices.is_empty() {
            ui.centered_and_justified(|ui| {
                ui.label(
                    RichText::new(if self.scanning {
                        "Analyse du réseau en cours…"
                    } else {
                        "Aucun appareil détecté sur ce réseau."
                    })
                    .color(MUTED)
                    .size(14.0),
                );
            });
            return;
        }

        let visible = self.visible();
        let mut clicked: Option<String> = None;
        let mut sort_request: Option<Column_> = None;

        let headers = [
            (Column_::Ip, "Adresse IP"),
            (Column_::Mac, "Adresse MAC"),
            (Column_::Vendor, "Fabricant"),
            (Column_::Host, "Nom d’hôte"),
            (Column_::Latency, "Latence"),
            (Column_::Label, "Étiquette"),
            (Column_::Status, ""),
        ];

        TableBuilder::new(ui)
            .striped(true)
            .sense(egui::Sense::click())
            .column(Column::auto().at_least(110.0))
            .column(Column::auto().at_least(140.0))
            .column(Column::initial(170.0).at_least(80.0).clip(true))
            .column(Column::initial(150.0).at_least(80.0).clip(true))
            .column(Column::auto().at_least(70.0))
            .column(Column::remainder().at_least(80.0).clip(true))
            .column(Column::auto().at_least(80.0))
            .header(26.0, |mut header| {
                for (column, title) in headers {
                    header.col(|ui| {
                        let arrow = if self.sort == column {
                            if self.sort_desc { " ▼" } else { " ▲" }
                        } else {
                            ""
                        };
                        let text = RichText::new(format!("{title}{arrow}")).strong().color(MUTED);
                        if ui.add(egui::Label::new(text).sense(egui::Sense::click())).clicked() {
                            sort_request = Some(column);
                        }
                    });
                }
            })
            .body(|body| {
                body.rows(28.0, visible.len(), |mut row| {
                    let device = &self.devices[visible[row.index()]];
                    row.set_selected(self.selected_mac.as_deref() == Some(device.mac.as_str()));

                    row.col(|ui| {
                        ui.label(device.ip.to_string());
                    });
                    row.col(|ui| {
                        ui.label(RichText::new(&device.mac).monospace());
                    });
                    row.col(|ui| {
                        ui.label(&device.vendor);
                    });
                    row.col(|ui| {
                        ui.label(if device.hostname.is_empty() { "—" } else { &device.hostname });
                    });
                    row.col(|ui| {
                        ui.label(device.latency_ms.map_or("—".to_string(), |ms| format!("{ms:.0} ms")));
                    });
                    row.col(|ui| {
                        ui.label(get_label(&self.labels, &device.mac));
                    });
                    row.col(|ui| {
                        if self.is_new(device) {
                            ui.label(RichText::new("NOUVEAU").color(WARN).strong());
                        }
                    });

                    if row.response().clicked() {
                        clicked = Some(device.mac.clone());
                    }
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
    }

    fn side_panel(&mut self, ui: &mut egui::Ui, ctx: &egui::Context) {
        ui.horizontal(|ui| {
            ui.selectable_value(&mut self.tab, Tab::Device, "Appareil");
            ui.selectable_value(&mut self.tab, Tab::Network, "Réseau");
        });
        ui.separator();

        egui::ScrollArea::vertical().show(ui, |ui| match self.tab {
            Tab::Device => self.device_tab(ui, ctx),
            Tab::Network => self.network_tab(ui, ctx),
        });
    }

    fn device_tab(&mut self, ui: &mut egui::Ui, ctx: &egui::Context) {
        let Some(device) = self.selected().cloned() else {
            ui.label(RichText::new("Sélectionnez un appareil.").color(MUTED));
            return;
        };

        ui.label(RichText::new("Appareil").size(14.0).strong());
        ui.add_space(6.0);
        field(ui, "Adresse IP", &device.ip.to_string());
        field(ui, "Adresse MAC", &device.mac);
        field(ui, "Fabricant", if device.vendor.is_empty() { "Inconnu" } else { &device.vendor });
        field(ui, "Nom d’hôte", if device.hostname.is_empty() { "Inconnu" } else { &device.hostname });
        field(
            ui,
            "Latence",
            &device.latency_ms.map_or("—".into(), |ms| format!("{ms:.0} ms")),
        );

        ui.label(RichText::new("Étiquette").color(MUTED));
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
        ui.label(RichText::new("Actions").color(MUTED));
        let width = ui.available_width();
        let button = |ui: &mut egui::Ui, text: &str, enabled: bool| {
            ui.add_enabled(enabled, egui::Button::new(text).min_size(egui::vec2(width, 30.0)))
        };

        let ip = device.ip;
        if button(ui, "Ping", !self.busy).clicked() {
            let (program, args) = ping_command(ip);
            self.spawn_output(ctx, format!("Ping · {ip}"), move || run_command(program, &args));
        }
        if button(ui, "Traceroute", !self.busy).clicked() {
            let (program, args) = traceroute_command(ip);
            self.spawn_output(ctx, format!("Traceroute · {ip}"), move || run_command(program, &args));
        }
        if button(ui, "Scanner les ports…", !self.busy).clicked() {
            self.ports_dialog = Some(String::new());
        }
        if button(ui, "Ouvrir dans le navigateur", true).clicked() {
            ctx.open_url(egui::OpenUrl::new_tab(format!("http://{ip}")));
        }
        if button(ui, "Réveiller (Wake-on-LAN)", true).clicked() {
            self.status = match wake_on_lan(&device.mac, Ipv4Addr::BROADCAST) {
                Ok(()) => format!("Paquet Wake-on-LAN envoyé à {}", device.mac),
                Err(error) => error,
            };
        }
        if button(ui, "Copier IP / MAC", true).clicked() {
            let text = format!("{}  {}", device.ip, device.mac);
            self.status = match arboard::Clipboard::new().and_then(|mut c| c.set_text(text)) {
                Ok(()) => "IP et MAC copiées dans le presse-papiers".into(),
                Err(error) => format!("Copie impossible : {error}"),
            };
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
                ui.label(RichText::new("Aucun réseau local détecté.").color(MUTED));
            }
        }

        ui.add_space(8.0);
        ui.label(RichText::new("Connexion Internet").size(14.0).strong());
        ui.add_space(6.0);
        match &self.public {
            None => {
                ui.label(RichText::new("Chargement…").color(MUTED));
            }
            Some(Err(error)) => {
                ui.label(RichText::new(error).color(MUTED));
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
                .color(MUTED)
                .small(),
        );
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
                match (parsed, self.selected().map(|d| d.ip)) {
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
                        ui.add(
                            egui::Label::new(RichText::new(text).monospace())
                                .selectable(true),
                        );
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

fn field(ui: &mut egui::Ui, name: &str, value: &str) {
    ui.label(RichText::new(name).color(MUTED).small());
    ui.add(egui::Label::new(if value.is_empty() { "—" } else { value }).selectable(true));
    ui.add_space(6.0);
}

fn apply_style(ctx: &egui::Context) {
    let mut visuals = egui::Visuals::dark();
    visuals.panel_fill = PANEL;
    visuals.window_fill = BG;
    visuals.extreme_bg_color = Color32::from_rgb(0x0a, 0x11, 0x19);
    visuals.faint_bg_color = Color32::from_rgb(0x13, 0x1c, 0x27);
    visuals.selection.bg_fill = Color32::from_rgb(0x1f, 0x51, 0x85);
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
    visuals.widgets.inactive.bg_fill = Color32::from_rgb(0x17, 0x21, 0x2d);
    visuals.widgets.inactive.weak_bg_fill = Color32::from_rgb(0x17, 0x21, 0x2d);
    visuals.widgets.inactive.bg_stroke = egui::Stroke::new(1.0, BORDER);
    visuals.window_corner_radius = egui::CornerRadius::ZERO;
    ctx.set_visuals(visuals);
}

impl eframe::App for App {
    fn ui(&mut self, ui: &mut egui::Ui, _frame: &mut eframe::Frame) {
        let ctx = ui.ctx().clone();
        self.poll_messages();

        egui::Panel::top("top").show(ui, |ui| {
            ui.add_space(6.0);
            self.top_bar(ui, &ctx);
            ui.add_space(6.0);
        });

        egui::Panel::bottom("status").show(ui, |ui| {
            ui.label(RichText::new(&self.status).color(MUTED));
        });

        egui::Panel::right("inspector")
            .exact_size(330.0)
            .resizable(false)
            .show(ui, |ui| self.side_panel(ui, &ctx));

        egui::CentralPanel::default().show(ui, |ui| self.table(ui));

        self.dialogs(&ctx);
    }
}

fn main() -> eframe::Result {
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_title("NetScanPy")
            .with_inner_size([1280.0, 760.0])
            .with_min_inner_size([1040.0, 600.0]),
        ..Default::default()
    };
    eframe::run_native("NetScanPy", options, Box::new(|cc| Ok(Box::new(App::new(cc)))))
}
