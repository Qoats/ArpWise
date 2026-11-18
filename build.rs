// Embeds the icon and publisher information into the Windows executables.
fn main() {
    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("windows") {
        let mut res = winresource::WindowsResource::new();
        res.set_icon("assets/icon.ico");
        res.set("CompanyName", "Qoats");
        res.set("ProductName", "ArpWise");
        res.set("FileDescription", "ArpWise - local network scanner");
        res.set("LegalCopyright", "Copyright (c) Qoats");
        if let Err(error) = res.compile() {
            // A missing resource compiler must not break the build.
            println!("cargo:warning=could not embed Windows resources: {error}");
        }
    }
    println!("cargo:rerun-if-changed=assets/icon.ico");
}
