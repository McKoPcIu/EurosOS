"""Read-only helpers for Euros EMS meter telemetry on the existing /Dev MQTT topic.

METER_1 is the electricity meter for the whole home's grid connection,
NOT a dedicated meter for the Euros heat pump. Future METER_2/METER_3
can be supported without changing these identifiers.
"""

import math
import re

EMS_DOM_METER_NAME = "METER_1"
EMS_DOM_DEVICE_NAME = "EMS – Dom"

# key: (name, unit, icon, sensor device class, state class)
# Values from /Dev METER_1 are already scaled to these units.
EMS_DOM_SENSOR_DEFINITIONS = {
    "TOTAL_ACT_POW_FL_1": ("EMS – Dom – Bilans mocy chwilowej", "kW", "mdi:transmission-tower", "power", "measurement"),
    "POS_ACT_POW_FL_1": ("EMS – Dom – Energia pobrana z sieci", "kWh", "mdi:transmission-tower-import", "energy", "total_increasing"),
    "REW_ACT_POW_FL_1": ("EMS – Dom – Energia oddana do sieci", "kWh", "mdi:transmission-tower-export", "energy", "total_increasing"),
    "A_PHA_VOLT_FL_1": ("EMS – Dom – Napięcie L1", "V", "mdi:flash", "voltage", "measurement"),
    "B_PHA_VOLT_FL_1": ("EMS – Dom – Napięcie L2", "V", "mdi:flash", "voltage", "measurement"),
    "C_PHA_VOLT_FL_1": ("EMS – Dom – Napięcie L3", "V", "mdi:flash", "voltage", "measurement"),
    "A_PHA_CUR_FL_1": ("EMS – Dom – Prąd L1", "A", "mdi:current-ac", "current", "measurement"),
    "B_PHA_CUR_FL_1": ("EMS – Dom – Prąd L2", "A", "mdi:current-ac", "current", "measurement"),
    "C_PHA_CUR_FL_1": ("EMS – Dom – Prąd L3", "A", "mdi:current-ac", "current", "measurement"),
    "FREQUENCY_FL_1": ("EMS – Dom – Częstotliwość sieci", "Hz", "mdi:sine-wave", "frequency", "measurement"),
    # Stage 1: fifteen additional directly reported electrical measurements.
    "AB_LINE_VOLT_FL_1": ("EMS – Dom – Napięcie L1–L2", "V", "mdi:flash", "voltage", "measurement"),
    "BC_LINE_VOLT_FL_1": ("EMS – Dom – Napięcie L2–L3", "V", "mdi:flash", "voltage", "measurement"),
    "CA_LINE_VOLT_FL_1": ("EMS – Dom – Napięcie L3–L1", "V", "mdi:flash", "voltage", "measurement"),
    "A_PHA_ACT_POW_FL_1": ("EMS – Dom – Moc czynna L1", "kW", "mdi:flash", "power", "measurement"),
    "B_PHA_ACT_POW_FL_1": ("EMS – Dom – Moc czynna L2", "kW", "mdi:flash", "power", "measurement"),
    "C_PHA_ACT_POW_FL_1": ("EMS – Dom – Moc czynna L3", "kW", "mdi:flash", "power", "measurement"),
    "TOTAL_RACT_POW_FL_1": ("EMS – Dom – Moc bierna całkowita", "kvar", "mdi:sine-wave", "reactive_power", "measurement"),
    "A_PHA_VIEW_POW_FL_1": ("EMS – Dom – Moc pozorna L1", "kVA", "mdi:flash-outline", "apparent_power", "measurement"),
    "B_PHA_VIEW_POW_FL_1": ("EMS – Dom – Moc pozorna L2", "kVA", "mdi:flash-outline", "apparent_power", "measurement"),
    "C_PHA_VIEW_POW_FL_1": ("EMS – Dom – Moc pozorna L3", "kVA", "mdi:flash-outline", "apparent_power", "measurement"),
    "TOTAL_APPA_POWER_FL_1": ("EMS – Dom – Moc pozorna całkowita", "kVA", "mdi:flash-outline", "apparent_power", "measurement"),
    "A_PHA_POW_FAC_FL_1": ("EMS – Dom – Współczynnik mocy L1", None, "mdi:angle-acute", "power_factor", "measurement"),
    "B_PHA_POW_FAC_FL_1": ("EMS – Dom – Współczynnik mocy L2", None, "mdi:angle-acute", "power_factor", "measurement"),
    "C_PHA_POW_FAC_FL_1": ("EMS – Dom – Współczynnik mocy L3", None, "mdi:angle-acute", "power_factor", "measurement"),
    "TOTAL_POW_FAC_FL_1": ("EMS – Dom – Współczynnik mocy całkowity", None, "mdi:angle-acute", "power_factor", "measurement"),
    # Stage 2: raw reactive energy counters from METER_1 (units in kvarh).
    "POS_REAC_POW_FL_1": ("EMS – Dom – Energia bierna dodatnia", "kvarh", "mdi:counter", "reactive_energy", "total_increasing"),
    "REW_REAC_POW_FL_1": ("EMS – Dom – Energia bierna ujemna", "kvarh", "mdi:counter", "reactive_energy", "total_increasing"),
    # Six diagnostic fields, deliberately not interpreted as regular grid power or PF.
    "A_ACT_POW_FL_1": ("EMS – Dom – Moc L1 – odczyt techniczny", "kW", "mdi:chart-line", "power", "measurement"),
    "B_ACT_POW_FL_1": ("EMS – Dom – Moc L2 – odczyt techniczny", "kW", "mdi:chart-line", "power", "measurement"),
    "C_ACT_POW_FL_1": ("EMS – Dom – Moc L3 – odczyt techniczny", "kW", "mdi:chart-line", "power", "measurement"),
    "POS_ACT_POW_FACTOR": ("EMS – Dom – Współczynnik POS – techniczny", None, "mdi:cog-outline", None, None),
    "REV_ACT_POW_FACTOR": ("EMS – Dom – Współczynnik REV – techniczny", None, "mdi:cog-outline", None, None),
    "TOTAL_ACT_POW_FACTOR": ("EMS – Dom – Współczynnik TOTAL – techniczny", None, "mdi:cog-outline", None, None),
}


# Human-readable measurement descriptions used by the EMS inventory/documentation.
# The first ten stable sensor definitions and their IDs remain unchanged.
EMS_DOM_STAGE_1_DESCRIPTIONS = {
    "AB_LINE_VOLT_FL_1": "Napięcie międzyfazowe pomiędzy fazami L1 i L2 mierzone przez licznik EMS na przyłączu całego domu.",
    "BC_LINE_VOLT_FL_1": "Napięcie międzyfazowe pomiędzy fazami L2 i L3 mierzone przez licznik EMS na przyłączu całego domu.",
    "CA_LINE_VOLT_FL_1": "Napięcie międzyfazowe pomiędzy fazami L3 i L1 mierzone przez licznik EMS na przyłączu całego domu.",
    "A_PHA_ACT_POW_FL_1": "Moc czynna przepływająca na fazie L1 w punkcie licznika EMS domu; wartość może mieć znak dodatni lub ujemny.",
    "B_PHA_ACT_POW_FL_1": "Moc czynna przepływająca na fazie L2 w punkcie licznika EMS domu; wartość może mieć znak dodatni lub ujemny.",
    "C_PHA_ACT_POW_FL_1": "Moc czynna przepływająca na fazie L3 w punkcie licznika EMS domu; wartość może mieć znak dodatni lub ujemny.",
    "TOTAL_RACT_POW_FL_1": "Łączna chwilowa moc bierna zmierzona na przyłączu całego domu; zachowujemy znak raportowany przez licznik.",
    "A_PHA_VIEW_POW_FL_1": "Moc pozorna na fazie L1 na przyłączu domu, obejmująca składowe czynną i bierną.",
    "B_PHA_VIEW_POW_FL_1": "Moc pozorna na fazie L2 na przyłączu domu, obejmująca składowe czynną i bierną.",
    "C_PHA_VIEW_POW_FL_1": "Moc pozorna na fazie L3 na przyłączu domu, obejmująca składowe czynną i bierną.",
    "TOTAL_APPA_POWER_FL_1": "Łączna chwilowa moc pozorna na przyłączu domu, raportowana bezpośrednio przez EMS.",
    "A_PHA_POW_FAC_FL_1": "Bezwymiarowy współczynnik mocy (cos φ / PF) fazy L1; zachowujemy znak raportowany przez EMS.",
    "B_PHA_POW_FAC_FL_1": "Bezwymiarowy współczynnik mocy (cos φ / PF) fazy L2; zachowujemy znak raportowany przez EMS.",
    "C_PHA_POW_FAC_FL_1": "Bezwymiarowy współczynnik mocy (cos φ / PF) fazy L3; zachowujemy znak raportowany przez EMS.",
    "TOTAL_POW_FAC_FL_1": "Łączny współczynnik mocy na przyłączu domu; wartości od −1 do 1, o ile raportowane przez EMS.",
}


# Stage 2 field names and comments derived from the actual METER_1 /Dev log.
# Raw technical power channels do NOT match the A/B/C_PHA_ACT_POW_FL_1 values.
# POS/REV/TOTAL factors are 1/1/-1 across all 1659 sampled packets;
# their detailed controller semantics must not be inferred from those numbers.
EMS_DOM_STAGE_2_DESCRIPTIONS = {
    "POS_REAC_POW_FL_1": "Narastający licznik energii biernej o kierunku dodatnim z METER_1, w kvarh. Nie interpretować znaku jako rodzaju obciążenia bez dokumentacji licznika.",
    "REW_REAC_POW_FL_1": "Narastający licznik energii biernej o kierunku ujemnym z METER_1, w kvarh. Nie interpretować znaku jako rodzaju obciążenia bez dokumentacji licznika.",
    "A_ACT_POW_FL_1": "Surowy dodatkowy kanał mocy A (L1) w kW, inny od A_PHA_ACT_POW_FL_1. Znaczenie techniczne niepotwierdzone; nie używać do bilansu domu.",
    "B_ACT_POW_FL_1": "Surowy dodatkowy kanał mocy B (L2) w kW, inny od B_PHA_ACT_POW_FL_1. Znaczenie techniczne niepotwierdzone; nie używać do bilansu domu.",
    "C_ACT_POW_FL_1": "Surowy dodatkowy kanał mocy C (L3) w kW, inny od C_PHA_ACT_POW_FL_1. Znaczenie techniczne niepotwierdzone; nie używać do bilansu domu.",
    "POS_ACT_POW_FACTOR": "Stały w logach parametr techniczny POS (1); nie jest to współczynnik mocy fazy ani zużycie energii. Znaczenie niepotwierdzone.",
    "REV_ACT_POW_FACTOR": "Stały w logach parametr techniczny REV (1); nie jest to współczynnik mocy fazy ani zużycie energii. Znaczenie niepotwierdzone.",
    "TOTAL_ACT_POW_FACTOR": "Stały w logach parametr techniczny TOTAL (-1); nie jest to bilans mocy ani zużycie energii. Znaczenie niepotwierdzone.",
}
EMS_DOM_STAGE_2_DIAGNOSTIC_KEYS = frozenset({
    "A_ACT_POW_FL_1",
    "B_ACT_POW_FL_1",
    "C_ACT_POW_FL_1",
    "POS_ACT_POW_FACTOR",
    "REV_ACT_POW_FACTOR",
    "TOTAL_ACT_POW_FACTOR",
})


# Derived daily counters on the same device, updated from the lifetime kWh meters.
# All measurements are grid import/export for the entire home, not heat pump usage.
EMS_DOM_DAILY_SENSOR_DEFINITIONS = {
    "POS_ACT_POW_FL_1": (
        "EMS – Dom – Energia pobrana dzisiaj",
        "mdi:transmission-tower-import",
    ),
    "REW_ACT_POW_FL_1": (
        "EMS – Dom – Energia oddana dzisiaj",
        "mdi:transmission-tower-export",
    ),
}


def accumulate_ems_daily_energy(day, accumulated, previous_meter_total, today, raw_total):
    """Pure incremental daily totalizer for a cumulative physical kWh meter.

    Returns (local_day, accumulated_kwh, last_meter_kwh).
    The first reading after enabling a daily sensor (or an HA outage spanning
    midnight) establishes a baseline. The first such day is incomplete.
    Small negative fluctuations are ignored; significant counter resets
    rebase without injecting a huge fictitious daily consumption.
    """
    value = parse_ems_numeric(raw_total)
    if value is None or value < 0:
        return day, accumulated, previous_meter_total

    if day != today:
        return today, 0.0, value

    if previous_meter_total is None:
        return today, max(0.0, float(accumulated or 0.0)), value

    previous = parse_ems_numeric(previous_meter_total)
    if previous is None or previous < 0:
        return today, max(0.0, float(accumulated or 0.0)), value

    if value >= previous:
        increment = value - previous
        return today, round(max(0.0, float(accumulated or 0.0)) + increment, 4), value

    # Ignore small negative fluctuations without lowering the reference total.
    if previous - value < max(0.05, previous * 0.01):
        return today, max(0.0, float(accumulated or 0.0)), previous

    # A large drop means a physical meter reset/replacement or data discontinuity.
    # Keep the accrued daily amount and treat this sample as a new baseline.
    return today, max(0.0, float(accumulated or 0.0)), value


def extract_ems_meters(devices):
    """Return current METER_N -> Data mappings; ignore the pump and unknown devices.

    Only devices explicitly tagged Type=METER are accepted. No messages are
    published or new MQTT topics subscribed to.
    """
    if not isinstance(devices, list):
        return {}

    meters = {}
    for device in devices:
        if not isinstance(device, dict):
            continue
        name = device.get("Name")
        meter_type = device.get("Type")
        data = device.get("Data")
        if (
            isinstance(name, str)
            and re.fullmatch(r"METER_[1-9][0-9]*", name, re.IGNORECASE)
            and isinstance(meter_type, str)
            and meter_type.upper() == "METER"
            and isinstance(data, dict)
        ):
            meters[name.upper()] = data
    return meters


def parse_ems_numeric(value):
    """Return a finite numeric reading, or None if the field is absent/invalid.

    Zero is only returned when the meter *actually* reports zero.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) else None
