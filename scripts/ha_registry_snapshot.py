"""Private, local Home Assistant Euros OS registry baseline/compare tool.

Reads only three HA .storage JSON files. Does NOT alter .storage, MQTT, pumps,
config entries, the integration, or HA. Captures only entity registry identity
and device links, never config-entry secrets or passwords. A local snapshot
contains internal identifiers and MUST NOT be committed, uploaded, or shared.

Examples (only after operator approval):
  python3 ha_registry_snapshot.py capture --config /config \
    --output /config/euros_os_stage9_private/baseline.json
  python3 ha_registry_snapshot.py compare \
    --before /config/euros_os_stage9_private/baseline.json \
    --after /config/euros_os_stage9_private/after.json
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys


STORAGE_FILES = {
    "config_entries": "core.config_entries",
    "entities": "core.entity_registry",
    "devices": "core.device_registry",
}
SNAPSHOT_FORMAT = "euros-os-registry-v1"


def _load_storage(path: Path, field: str) -> list[dict]:
    # Reading HA's internal JSON representation is best effort: it is not a
    # public API, and changes to the format require a tool update.
    data = json.loads(path.read_text(encoding="utf-8"))
    records = data.get("data", {}).get(field)
    if not isinstance(records, list) or not all(isinstance(x, dict) for x in records):
        raise ValueError(f"Unsupported registry shape in {path.name}: {field}")
    return records


def capture(config: Path, *, domain: str = "euros_os") -> dict:
    storage = config / ".storage"
    entries = _load_storage(storage / STORAGE_FILES["config_entries"], "entries")
    entry_ids = {
        row["entry_id"] for row in entries
        if row.get("domain") == domain and isinstance(row.get("entry_id"), str)
    }
    if not entry_ids:
        raise ValueError(f"No config entry for integration domain {domain!r}")

    all_entities = _load_storage(storage / STORAGE_FILES["entities"], "entities")
    all_devices = _load_storage(storage / STORAGE_FILES["devices"], "devices")

    entities = []
    for row in all_entities:
        if row.get("config_entry_id") not in entry_ids:
            continue
        entity_id = row.get("entity_id")
        # HA Core 2026.11 does NOT persist a separate 'domain' field in
        # core.entity_registry. RegistryEntry derives it from entity_id.
        if not isinstance(entity_id, str) or "." not in entity_id:
            raise ValueError("An Euros OS entity has an invalid entity_id")
        entity_domain, entity_name = entity_id.split(".", 1)
        if not entity_domain or not entity_name:
            raise ValueError("An Euros OS entity has an invalid entity_id")
        stored_domain = row.get("domain")
        if stored_domain is not None and stored_domain != entity_domain:
            raise ValueError("An Euros OS entity has a conflicting domain")
        item = {
            "domain": entity_domain,
            "platform": row.get("platform"),
            "unique_id": row.get("unique_id"),
            "entity_id": entity_id,
            "device_id": row.get("device_id"),
        }
        if not all(isinstance(item[key], str) and item[key]
                   for key in ("domain", "platform", "unique_id", "entity_id")):
            raise ValueError("An Euros OS entity has incomplete registry identity")
        if item["device_id"] is not None and not isinstance(item["device_id"], str):
            raise ValueError("Unexpected entity device_id")
        entities.append(item)

    devices = []
    for row in all_devices:
        # HA Core 2026.11 stores one owning config_entry_id per device.
        # Older HA releases stored the list 'config_entries'; accept both
        # formats but never guess if neither is well-formed.
        if "config_entry_id" in row:
            owner = row["config_entry_id"]
            if owner is not None and not isinstance(owner, str):
                raise ValueError("Unexpected device config_entry_id format")
            linked = {owner} if owner is not None else set()
        else:
            legacy_linked = row.get("config_entries")
            if not isinstance(legacy_linked, list) or not all(
                isinstance(value, str) for value in legacy_linked
            ):
                raise ValueError("Unsupported device config entry storage format")
            linked = set(legacy_linked)
        if not entry_ids.intersection(linked):
            continue
        device_id = row.get("id")
        if not isinstance(device_id, str) or not device_id:
            raise ValueError("Device lacks a registry ID")
        via = row.get("via_device_id")
        if via is not None and not isinstance(via, str):
            raise ValueError("Unexpected via_device_id")
        devices.append({"id": device_id, "via_device_id": via})

    entity_keys = [(x["domain"], x["platform"], x["unique_id"]) for x in entities]
    if len(entity_keys) != len(set(entity_keys)):
        raise ValueError("Duplicate Euros OS entity registry keys")
    if len({x["entity_id"] for x in entities}) != len(entities):
        raise ValueError("Duplicate Euros OS entity_id values")
    if len({x["id"] for x in devices}) != len(devices):
        raise ValueError("Duplicate Euros OS device IDs")
    registered_devices = {d["id"] for d in devices}
    if any(e["device_id"] is not None and e["device_id"] not in registered_devices
           for e in entities):
        raise ValueError("An entity links to a device outside this Euros OS configuration")

    return {
        "format": SNAPSHOT_FORMAT,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "domain": domain,
        "entry_count": len(entry_ids),
        "entities": sorted(
            entities, key=lambda x: (x["domain"], x["platform"], x["unique_id"])
        ),
        "devices": sorted(devices, key=lambda x: x["id"]),
    }


def validate_snapshot(snapshot: dict) -> None:
    if not isinstance(snapshot, dict) or snapshot.get("format") != SNAPSHOT_FORMAT:
        raise ValueError("Invalid or unsupported snapshot version")
    if snapshot.get("domain") != "euros_os":
        raise ValueError("Wrong integration domain")
    entities = snapshot.get("entities")
    devices = snapshot.get("devices")
    if not isinstance(entities, list) or not isinstance(devices, list):
        raise ValueError("Snapshot lacks entity and device arrays")
    required = {"domain", "platform", "unique_id", "entity_id", "device_id"}
    if any(not isinstance(row, dict) or not required.issubset(row)
           for row in entities):
        raise ValueError("Invalid entity record")


def differences(before: dict, after: dict) -> dict[str, int]:
    validate_snapshot(before)
    validate_snapshot(after)
    before_entities = {
        (x["domain"], x["platform"], x["unique_id"]): x for x in before["entities"]
    }
    after_entities = {
        (x["domain"], x["platform"], x["unique_id"]): x for x in after["entities"]
    }
    before_devices = {x["id"]: x for x in before["devices"]}
    after_devices = {x["id"]: x for x in after["devices"]}
    common = before_entities.keys() & after_entities.keys()
    common_devices = before_devices.keys() & after_devices.keys()
    return {
        "before_entities": len(before["entities"]),
        "after_entities": len(after["entities"]),
        "missing_entities": len(before_entities.keys() - after_entities.keys()),
        "new_entities": len(after_entities.keys() - before_entities.keys()),
        "changed_entity_ids": sum(
            before_entities[k]["entity_id"] != after_entities[k]["entity_id"]
            for k in common
        ),
        "changed_device_links": sum(
            before_entities[k]["device_id"] != after_entities[k]["device_id"]
            for k in common
        ),
        "before_devices": len(before_devices),
        "after_devices": len(after_devices),
        "missing_devices": len(before_devices.keys() - after_devices.keys()),
        "new_devices": len(after_devices.keys() - before_devices.keys()),
        "changed_parent_links": sum(
            before_devices[k]["via_device_id"] != after_devices[k]["via_device_id"]
            for k in common_devices
        ),
    }


def save_private_snapshot(path: Path, snapshot: dict) -> None:
    # Never overwrite a baseline, and never write snapshots to a public repo
    # or stdout. The operator supplies a PRIVATE path on their HA host.
    if not path.parent.is_dir():
        raise ValueError("Output directory does not exist. Create it privately first.")
    data = (json.dumps(snapshot, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    pre = sub.add_parser("capture", help="Read .storage and save one private JSON snapshot")
    pre.add_argument("--config", type=Path, default=Path("/config"))
    pre.add_argument("--output", type=Path, required=True)
    pre.add_argument("--expected-entities", type=int, default=73)
    pre.add_argument("--expected-devices", type=int, default=2)
    cmp = sub.add_parser("compare", help="Compare registry snapshots (no HA access)")
    cmp.add_argument("--before", type=Path, required=True)
    cmp.add_argument("--after", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == "capture":
            snapshot = capture(args.config)
            n_entities = len(snapshot["entities"])
            n_devices = len(snapshot["devices"])
            if n_entities != args.expected_entities or n_devices != args.expected_devices:
                print(
                    "STOP: unexpected registry counts "
                    f"({n_entities} entities, {n_devices} devices). "
                    "No snapshot was saved; investigate before continuing.",
                    file=sys.stderr,
                )
                return 2
            save_private_snapshot(args.output, snapshot)
            print(
                f"Private baseline saved: {n_entities} entities, {n_devices} devices. "
                "Do not upload or paste the JSON into GitHub/chat."
            )
            return 0

        before = json.loads(args.before.read_text(encoding="utf-8"))
        after = json.loads(args.after.read_text(encoding="utf-8"))
        summary = differences(before, after)
        for key, value in summary.items():
            print(f"{key}={value}")
        changed = any(value != 0 for key, value in summary.items()
                      if key not in ("before_entities", "after_entities",
                                     "before_devices", "after_devices"))
        changed |= summary["before_entities"] != summary["after_entities"]
        changed |= summary["before_devices"] != summary["after_devices"]
        print("PASS: Registry identity unchanged" if not changed
              else "STOP: Registry changed; investigate before acceptance")
        return 2 if changed else 0
    except (ValueError, OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"STOP: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
