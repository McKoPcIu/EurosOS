"""
===============================================================================
Euros OS Home Assistant Custom Integration
===============================================================================

File        : sensor.py
Author      : Patryk "KoPcIu" Kopeć / https://github.com/McKoPcIu/EurosOS
Integration : euros_os
Version     : 0.1.0
Description : Custom integration for EurosEnergy and E-On devices.

===============================================================================
"""

import logging
import math
import time
from homeassistant.helpers import device_registry as dr
from homeassistant.components.sensor import RestoreSensor, SensorEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util
from homeassistant.core import callback
from .const import DOMAIN, CONF_KEY, CONF_IP, SENSORS_VARIABLES, MQTT_TIMEOUT
from .coordinator import EurosOSMQTTCoordinator
from .ems import (
    EMS_DOM_DEVICE_NAME,
    EMS_DOM_METER_NAME,
    EMS_DOM_SENSOR_DEFINITIONS,
    EMS_DOM_DAILY_SENSOR_DEFINITIONS,
    EMS_DOM_STAGE_1_DESCRIPTIONS,
    EMS_DOM_STAGE_2_DESCRIPTIONS,
    EMS_DOM_STAGE_2_DIAGNOSTIC_KEYS,
    accumulate_ems_daily_energy,
    parse_ems_numeric,
    discover_ems_sensor_keys,
    discover_ems_daily_keys,
    ems_meter_device_name,
    ems_meter_sensor_info,
)
from .geo import (
    GEO_DEVICE_TYPE,
    GEO_GROUND_SOURCE_DELTA_T,
    GEO_GROUND_SOURCE_DELTA_T_NAME,
    GEO_UPPER_SOURCE_DELTA_T,
    GEO_UPPER_SOURCE_DELTA_T_NAME,
    calculate_ground_source_delta_t,
    calculate_upper_source_delta_t,
    calculate_geo_operating_state,
    entity_supported_for_device,
    sensor_info_for_device,
)

_LOGGER = logging.getLogger("custom_components.euros_os")

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up sensors from a config entry."""
    entry_data = hass.data[DOMAIN][entry.entry_id]["entry_data"]
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    device_info = hass.data[DOMAIN][entry.entry_id]["device_info"]

    entities = []
    unique_prefix = entry_data.get(CONF_KEY, "---")
    device_type = entry_data.get("device_type")
    for key, info in SENSORS_VARIABLES.items():
        if not entity_supported_for_device(key, device_type):
            continue
        model_info = sensor_info_for_device(key, info, device_type)
        sensor_class = EurosOSLegacyEstimatedEnergySensor if key == "ZM_AC_IN_ENERGY" else EurosOSSensor
        entities.append(sensor_class(coordinator, key, model_info, unique_prefix, device_info, device_type=device_type))

    if device_type == GEO_DEVICE_TYPE:
        for key, label in (
            (GEO_GROUND_SOURCE_DELTA_T, GEO_GROUND_SOURCE_DELTA_T_NAME),
            (GEO_UPPER_SOURCE_DELTA_T, GEO_UPPER_SOURCE_DELTA_T_NAME),
        ):
            entities.append(
                EurosOSSensor(
                    coordinator,
                    key,
                    (label, "°C", "mdi:delta", "temperature"),
                    unique_prefix,
                    device_info,
                    device_type=device_type,
                )
            )

    # Meter discovery is independent of the pump model (GEO/ATMO/ALLINONE).
    # Only real METER_N messages create EMS entities; no phantom EMS devices.
    # These keys are stable across MQTT restarts, ordering, and missing packets.
    registered_ems_entities = set()
    parent_device = None

    @callback
    def _discover_new_meter_entities():
        nonlocal parent_device
        pending = []
        for meter_name, readings in sorted(coordinator.ems_meters.items()):
            sensor_keys = discover_ems_sensor_keys(meter_name, readings)
            daily_keys = discover_ems_daily_keys(meter_name, readings)
            unseen_sensors = [
                key for key in sensor_keys
                if ("sensor", meter_name, key) not in registered_ems_entities
            ]
            unseen_daily = [
                key for key in daily_keys
                if ("daily", meter_name, key) not in registered_ems_entities
            ]
            if not unseen_sensors and not unseen_daily:
                continue

            # Register the existing parent device once, and link each meter
            # by via_device_id without affecting the pump's registry identity.
            if parent_device is None:
                parent_device = dr.async_get(hass).async_get_or_create(
                    config_entry_id=entry.entry_id,
                    **device_info,
                )
            meter_device_info = {
                "identifiers": {(DOMAIN, f"{unique_prefix}_ems_{meter_name.lower()}")},
                "name": ems_meter_device_name(meter_name),
                "model": meter_name,
                "via_device_id": parent_device.id,
            }
            for key in unseen_sensors:
                pending.append(
                    EurosOSEMSMeterSensor(
                        coordinator, meter_name, key,
                        ems_meter_sensor_info(meter_name, key),
                        unique_prefix, meter_device_info,
                    )
                )
                registered_ems_entities.add(("sensor", meter_name, key))
            for key in unseen_daily:
                pending.append(
                    EurosOSEMSDailyEnergySensor(
                        coordinator, meter_name, key,
                        EMS_DOM_DAILY_SENSOR_DEFINITIONS[key],
                        unique_prefix, meter_device_info,
                    )
                )
                registered_ems_entities.add(("daily", meter_name, key))
        return pending

    entities.extend(_discover_new_meter_entities())
    async_add_entities(entities)

    @callback
    def _on_meter_discovery():
        new_entities = _discover_new_meter_entities()
        if new_entities:
            async_add_entities(new_entities)

    coordinator.async_add_listener(_on_meter_discovery)
    hass.data[DOMAIN][entry.entry_id]["meter_discovery_listener"] = _on_meter_discovery
    _LOGGER.info("Added %d initial sensor entities.", len(entities))


class EurosOSSensor(SensorEntity):
    def __init__(self, coordinator, key, info, unique_prefix, device_info, device_type=None):
        self.coordinator = coordinator
        self.device_type = device_type
        self.key = key
        self._attr_name = info[0]
        self._attr_native_unit_of_measurement = info[1]
        self._attr_icon = info[2]
        self._attr_device_class = info[3]
        self._attr_unique_id = f"{unique_prefix}_{key.lower()}"
        self._attr_device_info = device_info
        self._attr_state_class = (
            "total_increasing" if key == "ZM_AC_IN_ENERGY"
            else None if key in ("STATE", "MODE", "SW_VERSION")
            else "measurement"
        )


        coordinator.async_add_listener(self._handle_coordinator_update)


    @property
    def available(self):
        """Use HA's availability flag, not a literal 'unavailable' sensor value."""
        last_update = getattr(self.coordinator, "_last_update", None)
        return (
            last_update is not None
            and time.time() - last_update <= MQTT_TIMEOUT
        )

    @property
    def native_value(self):
        device = self.coordinator.device
        if not device:
            return None
        data = device.get("Data", {})

        if self.key == GEO_GROUND_SOURCE_DELTA_T:
            return calculate_ground_source_delta_t(data)
        if self.key == GEO_UPPER_SOURCE_DELTA_T:
            return calculate_upper_source_delta_t(data)

        if self.key == "STATE":
            if self.device_type == GEO_DEVICE_TYPE:
                # Never label missing/malformed GEO state flags as IDLE.
                return calculate_geo_operating_state(data)
            try:
                SBF_DHS = int(data.get("SBF_DHS", 0))
                SBF_DHX = int(data.get("SBF_DHX", 0))
                SBF_OOF = int(data.get("SBF_OOF", 0))
                SBB_QHW = int(data.get("SBB_QHW", 0))
                SXF_TOE = int(data.get("SXF_TOE", 0))
                SBB_QHT = int(data.get("SBB_QHT", 0))
                SBB_QHL = int(data.get("SBB_QHL", 0))
        
                if SBF_DHS == 1 and SBF_DHX == 1 and SBF_OOF == 1 and SBB_QHW == 1:
                    return "CWU"
                if SXF_TOE == 1 and SBF_OOF == 1 and (SBB_QHT == 1 or SBB_QHL == 1):
                    return "CO"
                return "IDLE"
            except Exception as e:
                _LOGGER.warning("Error analyzing state: %s", e)
                return "IDLE"

        if self.key == "SW_VERSION":
            ver1 = data.get("VER_S1")
            ver2 = data.get("VER_S2")
            if ver1 is not None and ver2 is not None:
                return f"{ver1}.{ver2}"
            return None

        if self.key == "MODE":
            try:
                SBF_OOF = int(data.get("SBF_OOF", 0))
                SXF_ECO = int(data.get("SXF_ECO", 0))
                SXF_AWA = int(data.get("SXF_AWA", 0))
                SXF_TIME = int(data.get("SXF_TIME", 0))

                # GEO / EMS Expert: observed in the 2026-10-30 AUTO/EMS tests.
                # This is a read-only, provisional mapping. Never infer EMS
                # from a missing/invalid U_ENE_TAR field.
                energy_tariff = data.get("U_ENE_TAR")

                if SBF_OOF == 0:
                    return "OFF"
                elif SBF_OOF == 1 and SXF_TIME == 1:
                    return "TIME"
                elif SBF_OOF == 1 and SXF_AWA == 1:
                    return "AWAY"
                elif SBF_OOF == 1 and SXF_ECO == 1:
                    return "ECO"
                elif SBF_OOF == 1 and SXF_ECO == 0 and SXF_AWA == 0 and SXF_TIME == 0:
                    if energy_tariff is not None:
                        try:
                            if int(energy_tariff) == 1:
                                return "EMS"
                        except (TypeError, ValueError):
                            pass
                    return "AUTO"
                else:
                    return "UNKNOWN"
            except (TypeError, ValueError) as e:
                _LOGGER.warning("Error analyzing operating mode: %s", e)
                return "UNKNOWN"

        if self.key == "ZM_AC_IN_PWR":
            try:
                amps = float(data["ZM_AC_IN_CUR"])
                volts = float(data["ZM_AC_IN_VOL"])
                if not (math.isfinite(amps) and math.isfinite(volts)):
                    return None
                return round(amps * volts, 2)
            except (KeyError, TypeError, ValueError, OverflowError):
                return None

        if getattr(self, "_attr_device_class", None) == "temperature":
            try:
                # A missing sensor field is not a real zero measurement.
                value = float(data.get(self.key))
                if not math.isfinite(value) or not -50 <= value <= 149:
                    return None
                return round(value, 1)
            except (TypeError, ValueError, OverflowError):
                return None

        raw = data.get(self.key)
        if self._attr_state_class is not None:
            if isinstance(raw, bool):
                return None
            try:
                numeric = float(raw)
            except (TypeError, ValueError, OverflowError):
                return None
            return numeric if math.isfinite(numeric) else None
        return raw

    @callback
    def _handle_coordinator_update(self):
        if self.hass:
            self.hass.loop.call_soon_threadsafe(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        self.coordinator.async_remove_listener(self._handle_coordinator_update)


class EurosOSLegacyEstimatedEnergySensor(RestoreSensor):
    """ATMO/ALLINONE estimated kWh from MQTT samples (not the EMS meter).

    Calculate only for successive fresh MQTT pump samples, never from a HA
    native_value getter. Persist a total across restarts through RestoreSensor.
    Skip gaps longer than MQTT_TIMEOUT rather than invent energy during outages.
    This deliberately retains the old entity unique_id for HA registry history.
    """

    _attr_should_poll = False

    def __init__(self, coordinator, key, info, unique_prefix, device_info, device_type=None):
        self.coordinator = coordinator
        self.device_type = device_type
        self.key = key
        self._attr_name = info[0]
        self._attr_icon = info[2]
        self._attr_device_class = "energy"
        self._attr_state_class = "total_increasing"
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_suggested_display_precision = 4
        self._attr_unique_id = f"{unique_prefix}_{key.lower()}"
        self._attr_device_info = device_info
        self._attr_native_value = None
        self._total_kwh = None
        self._last_timestamp = None
        self._last_power_w = None
        self._active = False
        coordinator.async_add_listener(self._handle_coordinator_update)

    @property
    def available(self):
        timestamp = getattr(self.coordinator, "_last_update", None)
        return (
            timestamp is not None
            and time.time() - timestamp <= MQTT_TIMEOUT
            and self._attr_native_value is not None
        )

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        restored = await self.async_get_last_sensor_data()
        if restored is not None:
            value = parse_ems_numeric(getattr(restored, "native_value", None))
            if value is not None and value >= 0:
                self._total_kwh = value
                self._attr_native_value = round(value, 4)
        self._active = True
        # Start from latest sample: do not count time while HA was offline.
        self._refresh_from_pump()

    @callback
    def _refresh_from_pump(self):
        if not self._active:
            return
        timestamp = getattr(self.coordinator, "_last_update", None)
        if timestamp is None or timestamp == self._last_timestamp:
            return
        if self._last_timestamp is not None and timestamp < self._last_timestamp:
            # A system-clock adjustment cannot create extra energy.
            self._last_power_w = None

        pump = getattr(self.coordinator, "device", None)
        data = pump.get("Data") if isinstance(pump, dict) else None
        power_w = None
        if isinstance(data, dict):
            amps = parse_ems_numeric(data.get("ZM_AC_IN_CUR"))
            volts = parse_ems_numeric(data.get("ZM_AC_IN_VOL"))
            if amps is not None and volts is not None and amps >= 0 and volts >= 0:
                power_w = amps * volts
                if not math.isfinite(power_w):
                    power_w = None

        if power_w is not None:
            if self._total_kwh is None:
                self._total_kwh = 0.0
            if (
                self._last_timestamp is not None
                and self._last_power_w is not None
                and 0 < timestamp - self._last_timestamp <= MQTT_TIMEOUT
            ):
                # Trapezoidal estimate: power(W) × time(s) / 3,600,000.
                increment = (
                    (self._last_power_w + power_w) / 2
                    * (timestamp - self._last_timestamp)
                    / 3_600_000
                )
                self._total_kwh += increment
            self._attr_native_value = round(self._total_kwh, 4)

        # Invalid or missing power breaks the integration interval.
        self._last_timestamp = timestamp
        self._last_power_w = power_w
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self):
        if self._active and self.hass and not self.hass.loop.is_closed():
            self.hass.loop.call_soon_threadsafe(self._refresh_from_pump)

    async def async_will_remove_from_hass(self):
        self._active = False
        self.coordinator.async_remove_listener(self._handle_coordinator_update)


class EurosOSEMSMeterSensor(SensorEntity):
    """Read-only, directly metered electricity measurements for the whole home."""

    def __init__(self, coordinator, meter_name, key, info, unique_prefix, device_info):
        self.coordinator = coordinator
        self.meter_name = meter_name
        self.key = key
        name, unit, icon, device_class, state_class = info
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        if meter_name != EMS_DOM_METER_NAME:
            self._attr_extra_state_attributes = {
                "licznik": meter_name,
                "parametr_mqtt": key,
            }
        elif key in EMS_DOM_STAGE_1_DESCRIPTIONS:
            self._attr_extra_state_attributes = {
                "opis": EMS_DOM_STAGE_1_DESCRIPTIONS[key],
                "licznik": EMS_DOM_METER_NAME,
            }
        elif key in EMS_DOM_STAGE_2_DESCRIPTIONS:
            self._attr_extra_state_attributes = {
                "opis": EMS_DOM_STAGE_2_DESCRIPTIONS[key],
                "licznik": EMS_DOM_METER_NAME,
                "parametr_mqtt": key,
            }
            if key in EMS_DOM_STAGE_2_DIAGNOSTIC_KEYS:
                self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_unique_id = f"{unique_prefix}_ems_{meter_name.lower()}_{key.lower()}"
        self._attr_device_info = device_info

        coordinator.async_add_listener(self._handle_coordinator_update)

    @property
    def native_value(self):
        readings = self.coordinator.ems_meters.get(self.meter_name)
        if not isinstance(readings, dict):
            return None
        return parse_ems_numeric(readings.get(self.key))

    @property
    def available(self):
        last_update = self.coordinator._meter_last_update.get(self.meter_name)
        return (
            last_update is not None
            and time.time() - last_update <= MQTT_TIMEOUT
            and self.native_value is not None
        )

    @callback
    def _handle_coordinator_update(self):
        if self.hass and not self.hass.loop.is_closed():
            self.hass.loop.call_soon_threadsafe(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        self.coordinator.async_remove_listener(self._handle_coordinator_update)


class EurosOSEMSDailyEnergySensor(RestoreSensor):
    """Daily home grid import/export energy, derived from METER_1 lifetime kWh.

    The counter starts at the first available meter reading on installation
    and restores its current-day state after HA restarts. Midnight rollover
    follows the HA configured local timezone. Never publishes MQTT commands.
    """

    _attr_should_poll = False

    def __init__(self, coordinator, meter_name, key, info, unique_prefix, device_info):
        self.coordinator = coordinator
        self.meter_name = meter_name
        self.key = key
        name, icon = info
        self._attr_name = name
        self._attr_icon = icon
        self._attr_device_class = "energy"
        self._attr_state_class = "total_increasing"
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_suggested_display_precision = 2
        self._attr_unique_id = (
            f"{unique_prefix}_ems_{meter_name.lower()}_daily_{key.lower()}"
        )
        self._attr_device_info = device_info

        self._day = dt_util.now().date().isoformat()
        self._last_meter_total = None
        self._attr_native_value = None
        self._active = False
        coordinator.async_add_listener(self._handle_coordinator_update)

    @property
    def extra_state_attributes(self):
        return {
            "ems_day": self._day,
            "last_meter_kwh": self._last_meter_total,
            "meter": self.meter_name,
        }

    @property
    def available(self):
        last_update = self.coordinator._meter_last_update.get(self.meter_name)
        readings = self.coordinator.ems_meters.get(self.meter_name)
        return (
            last_update is not None
            and time.time() - last_update <= MQTT_TIMEOUT
            and isinstance(readings, dict)
            and parse_ems_numeric(readings.get(self.key)) is not None
            and self.native_value is not None
        )

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        restored = await self.async_get_last_state()
        today = dt_util.now().date().isoformat()
        if restored is not None and restored.attributes.get("ems_day") == today:
            restored_value = parse_ems_numeric(restored.state)
            restored_total = parse_ems_numeric(
                restored.attributes.get("last_meter_kwh")
            )
            if (
                restored_value is not None
                and restored_value >= 0
                and restored_total is not None
                and restored_total >= 0
            ):
                self._day = today
                self._attr_native_value = restored_value
                self._last_meter_total = restored_total

        self._active = True
        self.async_on_remove(
            async_track_time_change(
                self.hass, self._reset_at_midnight, hour=0, minute=0, second=0
            )
        )
        self._refresh_from_meter()

    @callback
    def _reset_at_midnight(self, now):
        """Start a new local day, retaining the last metered value as baseline."""
        if not self._active:
            return
        self._day = dt_util.now().date().isoformat()
        self._attr_native_value = 0.0
        # Retaining the previous counter avoids missing the first post-midnight
        # increment while HA is running; its timestamp can straddle midnight.
        self.async_write_ha_state()

    @callback
    def _refresh_from_meter(self):
        if not self._active:
            return
        readings = self.coordinator.ems_meters.get(self.meter_name)
        if not isinstance(readings, dict):
            self.async_write_ha_state()
            return
        raw = parse_ems_numeric(readings.get(self.key))
        if raw is None or raw < 0:
            self.async_write_ha_state()
            return

        today = dt_util.now().date().isoformat()
        day, value, last = accumulate_ems_daily_energy(
            self._day, self._attr_native_value,
            self._last_meter_total, today, raw
        )
        self._day = day
        self._attr_native_value = value
        self._last_meter_total = last
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self):
        if (
            self._active
            and self.hass
            and not self.hass.loop.is_closed()
        ):
            self.hass.loop.call_soon_threadsafe(self._refresh_from_meter)

    async def async_will_remove_from_hass(self):
        self._active = False
        self.coordinator.async_remove_listener(self._handle_coordinator_update)
