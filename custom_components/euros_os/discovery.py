"""Read-only identification of Euros OS heat pumps in MQTT /Dev payloads.

Meter discovery is intentionally separate and unchanged in this stage.
"""
from __future__ import annotations

SUPPORTED_PUMP_TYPES = frozenset({"FriskoGEO", "FriskoATMO", "FriskoALLINONE"})


def find_pump(devices, *, expected_name=None, expected_type=None):
    """Return the single matching pump or None; never select Devices[0] blindly.

    Existing entries can identify their configured pump by Name and Type.
    Ambiguous payloads without a configured identity are rejected.
    """
    if not isinstance(devices, list):
        return None
    candidates = [
        device for device in devices
        if isinstance(device, dict)
        and device.get("Type") in SUPPORTED_PUMP_TYPES
        and isinstance(device.get("Name"), str)
        and bool(device["Name"])
        and isinstance(device.get("Data"), dict)
    ]
    if expected_name is not None:
        candidates = [d for d in candidates if d["Name"] == expected_name]
    if expected_type is not None:
        candidates = [d for d in candidates if d["Type"] == expected_type]
    return candidates[0] if len(candidates) == 1 else None
