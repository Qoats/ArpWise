#!/usr/bin/env python3
"""Regenerate the Scoop and winget manifests for a release.

    python packaging/update_manifests.py 0.5.1 path/to/SHA256SUMS.txt

Writes:
  bucket/arpwise.json                                   (Scoop bucket)
  packaging/winget/*.yaml                               (winget manifests)

The hashes come straight from the SHA256SUMS.txt published with the release,
so they always match the files people download. Standard library only.
"""

import json
import sys
from pathlib import Path

OWNER_REPO = "Qoats/ArpWise"
HOMEPAGE = "https://qoats.github.io/ArpWise/"
DESCRIPTION = (
    "Fast, driver-free local network scanner: devices, manufacturers, "
    "latency, history and Wake-on-LAN."
)
ROOT = Path(__file__).resolve().parent.parent

# (scoop key, winget architecture, file-name architecture)
ARCHS = [("64bit", "x64", "x64"), ("32bit", "x86", "x86"), ("arm64", "arm64", "arm64")]


def read_sums(path):
    sums = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2:
            sums[parts[1].lstrip("*")] = parts[0].lower()
    return sums


def zip_name(version, arch):
    return f"ArpWise-{version}-windows-{arch}.zip"


def write_scoop(version, sums):
    base = f"https://github.com/{OWNER_REPO}/releases/download/v{version}"
    manifest = {
        "version": version,
        "description": DESCRIPTION,
        "homepage": HOMEPAGE,
        "license": "GPL-3.0-only",
        "architecture": {
            key: {
                "url": f"{base}/{zip_name(version, arch)}",
                "hash": sums[zip_name(version, arch)],
                "extract_dir": f"ArpWise-{version}-windows-{arch}",
            }
            for key, _, arch in ARCHS
        },
        "bin": ["arpwise.exe"],
        "shortcuts": [["arpwise-gui.exe", "ArpWise"]],
        "checkver": {"github": f"https://github.com/{OWNER_REPO}"},
        "autoupdate": {
            "architecture": {
                key: {
                    "url": f"https://github.com/{OWNER_REPO}/releases/download/v$version/ArpWise-$version-windows-{arch}.zip",
                    "extract_dir": f"ArpWise-$version-windows-{arch}",
                }
                for key, _, arch in ARCHS
            },
            "hash": {"url": "$baseurl/SHA256SUMS.txt"},
        },
    }
    target = ROOT / "bucket" / "arpwise.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(manifest, indent=4) + "\n", encoding="utf-8")
    print("wrote", target.relative_to(ROOT))


def write_winget(version, sums):
    base = f"https://github.com/{OWNER_REPO}/releases/download/v{version}"
    # Flat folder with the three files of the current version. To submit them,
    # copy them to manifests/q/Qoats/ArpWise/<version>/ in microsoft/winget-pkgs.
    folder = ROOT / "packaging" / "winget"
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.yaml"):  # keep only the current version
        old.unlink()

    header = "# yaml-language-server: $schema=https://aka.ms/winget-manifest.{kind}.1.6.0.schema.json\n"

    (folder / "Qoats.ArpWise.yaml").write_text(
        header.format(kind="version")
        + f"PackageIdentifier: Qoats.ArpWise\nPackageVersion: {version}\n"
        "DefaultLocale: en-US\nManifestType: version\nManifestVersion: 1.6.0\n",
        encoding="utf-8",
    )

    installers = ""
    for _, winget_arch, arch in ARCHS:
        name = zip_name(version, arch)
        folder_in_zip = f"ArpWise-{version}-windows-{arch}"
        installers += (
            f"- Architecture: {winget_arch}\n"
            f"  InstallerUrl: {base}/{name}\n"
            f"  InstallerSha256: {sums[name].upper()}\n"
            "  NestedInstallerFiles:\n"
            f"  - RelativeFilePath: {folder_in_zip}\\arpwise.exe\n"
            "    PortableCommandAlias: arpwise\n"
            f"  - RelativeFilePath: {folder_in_zip}\\arpwise-gui.exe\n"
            "    PortableCommandAlias: arpwise-gui\n"
        )
    (folder / "Qoats.ArpWise.installer.yaml").write_text(
        header.format(kind="installer")
        + f"PackageIdentifier: Qoats.ArpWise\nPackageVersion: {version}\n"
        "InstallerType: zip\nNestedInstallerType: portable\nInstallModes:\n- silent\n"
        "Installers:\n" + installers + "ManifestType: installer\nManifestVersion: 1.6.0\n",
        encoding="utf-8",
    )

    (folder / "Qoats.ArpWise.locale.en-US.yaml").write_text(
        header.format(kind="defaultLocale")
        + f"PackageIdentifier: Qoats.ArpWise\nPackageVersion: {version}\n"
        "PackageLocale: en-US\nPublisher: Qoats\n"
        f"PublisherUrl: {HOMEPAGE}\n"
        "PublisherSupportUrl: https://github.com/Qoats/ArpWise/issues\n"
        "PackageName: ArpWise\n"
        f"PackageUrl: {HOMEPAGE}\n"
        "License: GPL-3.0-only\n"
        f"LicenseUrl: https://github.com/{OWNER_REPO}/blob/main/LICENSE\n"
        f"ShortDescription: {DESCRIPTION}\n"
        "Moniker: arpwise\nTags:\n- network\n- scanner\n- arp\n- lan\n- wake-on-lan\n"
        "ManifestType: defaultLocale\nManifestVersion: 1.6.0\n",
        encoding="utf-8",
    )
    print("wrote", folder.relative_to(ROOT))


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    version = sys.argv[1].lstrip("v")
    sums = read_sums(sys.argv[2])
    missing = [zip_name(version, a) for _, _, a in ARCHS if zip_name(version, a) not in sums]
    if missing:
        sys.exit(f"SHA256SUMS.txt does not list: {', '.join(missing)}")
    write_scoop(version, sums)
    write_winget(version, sums)


if __name__ == "__main__":
    main()
