#!/usr/bin/env python3
"""Check every signed-index artifact with Ether's conformance kit."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

MAX_PACKAGE = 64 * 1024 * 1024
MAX_UNPACKED = 128 * 1024 * 1024

REMOVED_SECTIONS_FIELD_RE = re.compile(r"^ether\.contributes\.screens\[\d+\]\.(sections|pages)$")
REMOVED_SECTIONS_MESSAGES = {
    "fixed sections are gone: this plugin was built for an older Ether. Update it; screens are documents (pages) now",
    "must declare the screen's pages",
}


def parse_semver(raw):
    if not raw:
        return None
    core = raw.strip().lstrip("v").split("-", 1)[0].split("+", 1)[0]
    parts = core.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        return None
    return tuple(int(p) for p in parts)


def verify_catalogue_review(label, entry, version_entry, manifest):
    """Ensure the package manifest does not request kind, capabilities, or
    network hosts beyond the reviewed catalogue entry."""
    ether = manifest.get("ether") or {}
    if ether.get("kind") != entry.get("kind"):
        raise ValueError(
            f"{label}: manifest kind {ether.get('kind')!r} does not match catalogue entry kind {entry.get('kind')!r}"
        )
    reviewed_caps = set(entry.get("capabilities") or [])
    manifest_caps = set(ether.get("capabilities") or [])
    unreviewed_caps = sorted(manifest_caps - reviewed_caps)
    if unreviewed_caps:
        raise ValueError(f"{label}: manifest requests unreviewed capabilities: {', '.join(unreviewed_caps)}")
    reviewed_perms = version_entry.get("permissions") or entry.get("permissions") or {}
    reviewed_net = set(reviewed_perms.get("network") or [])
    manifest_perms = ether.get("permissions") or {}
    manifest_net = set(manifest_perms.get("network") or [])
    unreviewed_net = sorted(manifest_net - reviewed_net)
    if unreviewed_net:
        raise ValueError(f"{label}: manifest requests unreviewed network hosts: {', '.join(unreviewed_net)}")


def is_only_removed_sections_incompatibility(version_entry, manifest, legacy_max, json_stdout):
    """Return True only when:
    1. The version targets an older Ether line (minEther <= legacy_max),
    2. The manifest declares legacy contributes.screens[].sections without pages, and
    3. Every conformance error from the primary kit is the removed-sections
       hard-cut error (and its paired missing-pages error)."""
    if legacy_max is None:
        return False
    raw_min = version_entry.get("minEther") or (manifest.get("ether") or {}).get("minVersion") or ""
    min_ether = parse_semver(raw_min)
    if min_ether is None or min_ether > legacy_max:
        return False
    screens = ((manifest.get("ether") or {}).get("contributes") or {}).get("screens") or []
    if not any(isinstance(s, dict) and s.get("sections") and not s.get("pages") for s in screens):
        return False
    try:
        report = json.loads(json_stdout)
    except Exception:
        return False
    errors = report.get("errors") or []
    if not errors:
        return False
    saw_removed_sections = False
    for err in errors:
        if err.get("rule") != "manifest":
            return False
        field = err.get("field") or ""
        msg = err.get("message") or ""
        if not REMOVED_SECTIONS_FIELD_RE.match(field) or msg not in REMOVED_SECTIONS_MESSAGES:
            return False
        if field.endswith(".sections") and "fixed sections are gone" in msg:
            saw_removed_sections = True
    return saw_removed_sections


def run_kit_check(label, plugin_dir, version_entry, manifest):
    ether_bin = os.environ.get("ETHER_BIN", "ether")
    legacy_bin = os.environ.get("ETHER_LEGACY_BIN", "").strip()
    legacy_max = parse_semver(os.environ.get("ETHER_LEGACY_MAX_MIN_ETHER", "0.3.20"))
    proc = subprocess.run([ether_bin, "plugin", "check", "--json", str(plugin_dir)], capture_output=True, text=True)
    if proc.returncode == 0:
        print(f"Checked {label}", flush=True)
        return
    if legacy_bin and is_only_removed_sections_incompatibility(version_entry, manifest, legacy_max, proc.stdout):
        print(
            f"{label}: primary kit rejected removed screen sections; checking with legacy kit ({legacy_bin})",
            flush=True,
        )
        subprocess.run([legacy_bin, "plugin", "check", str(plugin_dir)], check=True)
        print(f"Checked {label} (legacy kit)", flush=True)
        return
    subprocess.run([ether_bin, "plugin", "check", str(plugin_dir)], check=True)


def check(index_path):
    with open(index_path, encoding="utf-8") as source:
        index = json.load(source)
    for entry in index["entries"]:
        if entry.get("revoked"):
            continue
        for version in entry["versions"]:
            label = f'{entry["id"]} {version["version"]}'
            request = urllib.request.Request(version["url"], headers={"User-Agent": "Ether catalogue CI"})
            with urllib.request.urlopen(request, timeout=60) as response:
                data = response.read(MAX_PACKAGE + 1)
            if len(data) > MAX_PACKAGE:
                raise ValueError(f"{label}: package exceeds size limit")
            if hashlib.sha256(data).hexdigest() != version["sha256"].lower():
                raise ValueError(f"{label}: package digest mismatch")
            with tempfile.TemporaryDirectory(prefix="ether-catalogue-") as directory:
                root = Path(directory)
                archive_path = root / "package.etherpkg"
                archive_path.write_bytes(data)
                plugin_dir = root / "plugin"
                plugin_dir.mkdir()
                with zipfile.ZipFile(archive_path) as archive:
                    total = 0
                    names = set()
                    for item in archive.infolist():
                        path = PurePosixPath(item.filename)
                        if (path.is_absolute() or ".." in path.parts or "\\" in item.filename
                                or item.filename in names or (item.external_attr >> 16) & 0o170000 == 0o120000):
                            raise ValueError(f"{label}: unsafe package path")
                        names.add(item.filename)
                        total += item.file_size
                        if total > MAX_UNPACKED:
                            raise ValueError(f"{label}: unpacked package exceeds size limit")
                    archive.extractall(plugin_dir)
                manifest = json.loads((plugin_dir / "manifest.json").read_text(encoding="utf-8"))
                if manifest.get("id") != entry["id"] or manifest.get("version") != version["version"]:
                    raise ValueError(f"{label}: package identity does not match index")
                verify_catalogue_review(label, entry, version, manifest)
                run_kit_check(label, plugin_dir, version, manifest)


if __name__ == "__main__":
    try:
        check(sys.argv[1] if len(sys.argv) > 1 else "index.json")
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, subprocess.CalledProcessError) as exc:
        print(f"Catalogue check failed: {exc}", file=sys.stderr)
        sys.exit(1)
