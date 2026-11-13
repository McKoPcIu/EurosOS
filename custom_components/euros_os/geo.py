"""Model-specific helpers for Euros GEO heat pumps.

The source returns to the heat pump through T3fiz and the pump sends the
cooled fluid back to the ground through T4fiz. Both assignments have been
confirmed for FriskoGEO; other device types keep their original labels.
"""

import math
from collections.abc import Mapping

GEO_DEVICE_TYPE = "FriskoGEO"
GEO_MANUFACTURER = "Euros Energy"


# P1 audit (2026-10-29): GEO_1 does not report these five readings in 357
# sampled /Dev messages. Legacy audit keys retained for compatibility; actual
# entity creation is controlled by GEO_EXCLUDED_ENTITIES below.
# Do not alias these fields to the whole-home METER_1.
GEO_P1_UNVERIFIED_SENSOR_KEYS = frozenset({
    "ZM_AC_IN_VOL",
    "ZM_AC_IN_CUR",
    "ZM_AC_IN_PWR",
    "ZM_AC_IN_ENERGY",
    "ZM_SUCT_TEMP",
})

_GEO_STATE_REQUIRED_KEYS = (
    "SBF_DHS",
    "SBF_DHX",
    "SBF_OOF",
    "SBB_QHW",
    "SXF_TOE",
    "SBB_QHT",
    "SBB_QHL",
)


def calculate_geo_operating_state(data: Mapping[str, object] | None) -> str | None:
    """Derive CWU/CO/IDLE/OFF state only from complete binary data.

    An incomplete or malformed /Dev packet is not evidence of IDLE or OFF. Keep the
    original state priority and meanings for fully valid FriskoGEO packets.
    This helper is read-only and does not affect heat-pump control commands.
    """
    if not isinstance(data, Mapping):
        return None

    flags = {}
    for key in _GEO_STATE_REQUIRED_KEYS:
        raw = data.get(key)
        # Only actual 0/1 readings are accepted; do not turn None or blanks
        # into 0, and do not silently accept floats or out-of-range integers.
        if isinstance(raw, bool):
            return None
        if isinstance(raw, int):
            value = raw
        elif isinstance(raw, str) and raw.strip() in ("0", "1"):
            value = int(raw.strip())
        else:
            return None
        if value not in (0, 1):
            return None
        flags[key] = value

    # SBF_OOF=0 denotes the explicitly disabled mode in this controller.
    # It must not be presented as a pump waiting in IDLE.
    if flags["SBF_OOF"] == 0:
        return "OFF"

    if (
        flags["SBF_DHS"] == 1
        and flags["SBF_DHX"] == 1
        and flags["SBF_OOF"] == 1
        and flags["SBB_QHW"] == 1
    ):
        return "CWU"
    if (
        flags["SXF_TOE"] == 1
        and flags["SBF_OOF"] == 1
        and (flags["SBB_QHT"] == 1 or flags["SBB_QHL"] == 1)
    ):
        return "CO"
    return "IDLE"

# GEO-specific exclusions: do not create new entities, but leave existing
# Home Assistant registry entries and their history intact (unavailable).
# The first three are air-source-only; other unavailable GEO measurements
# and unverified writable pressure calibration controls are also excluded.
# Keep STATE enabled: the operating-state sensor is explicitly NOT excluded.
GEO_EXCLUDED_ENTITIES = frozenset({
    "ZM_FAN1_SPE",
    "ZM_FAN2_SPE",
    "ZM_DEFR_SIGN",
    "ZM_AC_IN_VOL",
    "ZM_AC_IN_CUR",
    "ZM_AC_IN_PWR",
    "ZM_AC_IN_ENERGY",
    "ZM_SUCT_TEMP",
    "PWM_1",          # Legacy heating circulation pump percentage; absent in FriskoGEO MQTT
    "ZM_CUR_COMP_FREQ",  # Compressor frequency absent from FriskoGEO MQTT; retain SIO_R06 on/off state
    "ADC_1",          # CO pressure reading absent from FriskoGEO MQTT
    "ADC_2",          # CWU pressure reading absent from FriskoGEO MQTT
    "ADC_1_Factor_2",  # Unverified CO pressure calibration control; hide writable GEO entity
    "ADC_2_Factor_2",  # Unverified CWU pressure calibration control; hide writable GEO entity
})


def entity_supported_for_device(key: str, device_type: str | None) -> bool:
    """Do not create excluded GEO entities; preserve other models unchanged."""
    return device_type != GEO_DEVICE_TYPE or key not in GEO_EXCLUDED_ENTITIES

GEO_SENSOR_NAME_OVERRIDES = {
    "T3fiz": "Dolne źródło — temperatura powrotu z gruntu",
    "T4fiz": "Dolne źródło — temperatura wyjścia do gruntu",
    "T5fiz": "Górne źródło — temperatura powrotu",
    "TSM13": "Górne źródło — temperatura zasilania",
    "TSM15": "CWU — temperatura zbiornika",
    "TSM17": "CO — temperatura zbiornika",
    "SX5": "CWU — temperatura zadana zbiornika",
    "SX6": "CO — temperatura zadana pomieszczenia",
    "TSM10": "Temperatura wewnętrzna - aktualna",
    "TSM9": "Temperatura zewnętrzna - aktualna",
    "TOUT_KOR": "Temperatura zewnętrzna - średnia z pompy",
    "TSM16": "Temp. wejściowa czynnika (sprężarka)",
}

GEO_GROUND_SOURCE_DELTA_T = "GEO_GROUND_SOURCE_DELTA_T"
GEO_GROUND_SOURCE_DELTA_T_NAME = "Dolne źródło — temperatura różnicowa (ΔT)"

GEO_UPPER_SOURCE_DELTA_T = "GEO_UPPER_SOURCE_DELTA_T"
GEO_UPPER_SOURCE_DELTA_T_NAME = "Górne źródło — temperatura różnicowa (ΔT)"


def geo_device_software_version(device: Mapping[str, object] | None) -> str | None:
    """Read GEO firmware version from live MQTT fields VER_S1 and VER_S2.

    This matches the existing SW_VERSION entity; MQTT's outer Version field
    describes the payload and is not used as the firmware version.
    """
    if not isinstance(device, Mapping):
        return None
    data = device.get("Data")
    if not isinstance(data, Mapping):
        return None
    major = data.get("VER_S1")
    minor = data.get("VER_S2")
    if major is None or minor is None:
        return None
    major_text = str(major).strip()
    minor_text = str(minor).strip()
    if not major_text.isdecimal() or not minor_text.isdecimal():
        return None
    return f"{major_text}.{minor_text}"


def sensor_info_for_device(key: str, info: tuple, device_type: str | None) -> tuple:
    """Override only GEO labels, retaining units, icons and other metadata."""
    if device_type != GEO_DEVICE_TYPE:
        return info
    label = GEO_SENSOR_NAME_OVERRIDES.get(key)
    return (label, *info[1:]) if label else info


def _calculate_delta_t(
    data: Mapping[str, object], warm_sensor: str, cool_sensor: str
) -> float | None:
    """Calculate a temperature difference without treating absent values as zero."""
    try:
        warm_temp = float(data[warm_sensor])
        cool_temp = float(data[cool_sensor])
    except (KeyError, TypeError, ValueError):
        return None

    if not (math.isfinite(warm_temp) and math.isfinite(cool_temp)):
        return None
    if not (-50 <= warm_temp <= 149 and -50 <= cool_temp <= 149):
        return None

    return round(warm_temp - cool_temp, 1)


def calculate_ground_source_delta_t(data: Mapping[str, object]) -> float | None:
    """Return from ground (T3fiz) minus outlet to ground (T4fiz), in °C."""
    return _calculate_delta_t(data, "T3fiz", "T4fiz")


def calculate_upper_source_delta_t(data: Mapping[str, object]) -> float | None:
    """Heating-side supply (TSM13) minus return (T5fiz), in °C."""
    return _calculate_delta_t(data, "TSM13", "T5fiz")
