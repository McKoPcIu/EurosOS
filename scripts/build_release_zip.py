"""Build and validate the Euros OS integration ZIP for HACS / HA Marketplace.

This script NEVER creates a GitHub release. It builds a local ZIP whose root
contains manifest.json, __init__.py, platforms, and translations so that
Marketplace can extract it directly to custom_components/euros_os/.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "euros_os"
HACS = ROOT / "hacs.json"
EXCLUDED_DIRS = {"__pycache__", ".git", ".pytest_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".swp", ".tmp"}


def build_archive(output: Path) -> tuple[str, ...]:
    settings = json.loads(HACS.read_text(encoding="utf-8"))
    manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
    if settings.get("domain") != manifest.get("domain") or manifest["domain"] != "euros_os":
        raise ValueError("HACS domain and integration manifest domain differ")
    if not settings.get("zip_release") or settings.get("filename") != "euros_os.zip":
        raise ValueError("Expected zip_release: true and filename euros_os.zip")
    if not manifest.get("version") or not manifest.get("config_flow"):
        raise ValueError("Missing version or config flow in integration manifest")
    files = sorted(
        file for file in INTEGRATION.rglob("*")
        if file.is_file()
        and not file.is_symlink()
        and not (set(file.relative_to(INTEGRATION).parts) & EXCLUDED_DIRS)
        and file.suffix not in EXCLUDED_SUFFIXES
    )
    names = [file.relative_to(INTEGRATION).as_posix() for file in files]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate paths in release archive")
    required = {"__init__.py", "manifest.json", "config_flow.py", "sensor.py", "coordinator.py"}
    if not required.issubset(names):
        raise ValueError(f"Missing required integration files: {sorted(required - set(names))}")
    if not any(x.startswith("translations/") and x.endswith(".json") for x in names):
        raise ValueError("Missing localization files")

    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file, name in zip(files, names):
            archive.write(file, name)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None or archive.namelist() != names:
            raise ValueError("Archive corruption or mismatched members")
        if json.loads(archive.read("manifest.json"))["domain"] != manifest["domain"]:
            raise ValueError("Wrong domain inside release archive")
    return tuple(names)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "euros_os.zip")
    args = parser.parse_args()
    files = build_archive(args.output)
    print(f"Verified {args.output} with {len(files)} integration files.")


if __name__ == "__main__":
    main()
