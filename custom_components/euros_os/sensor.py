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
import time
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback
from .const import DOMAIN, CONF_KEY, CONF_IP, SENSORS_VARIABLES, MQTT_TIMEOUT
from .coordinator import EurosOSMQTTCoordinator

_LOGGER = logging.getLogger("custom_components.euros_os")

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up sensors from a config entry."""
    entry_data = hass.data[DOMAIN][entry.entry_id]["entry_data"]
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    device_info = hass.data[DOMAIN][entry.entry_id]["device_info"]

    entities = []
    unique_prefix = entry_data.get(CONF_KEY, "---")
    for key, info in SENSORS_VARIABLES.items():
        entities.append(EurosOSSensor(coordinator, key, info, unique_prefix, device_info))

    async_add_entities(entities)
    _LOGGER.info("Added %d sensors entities.", len(entities))


class EurosOSSensor(SensorEntity):
    def __init__(self, coordinator, key, info, unique_prefix, device_info):
        self.coordinator = coordinator
        self.key = key
        self._attr_name = info[0]
        self._unit = info[1] #self._attr_unit_of_measurement = info[1]
        self._attr_icon = info[2]
        self._attr_device_class = info[3]
        self._attr_unique_id = f"{unique_prefix}_{key.lower()}"
        self._attr_device_info = device_info

        self._last_energy_update = None
        self._energy_kwh = 0.0


        coordinator.async_add_listener(self._handle_coordinator_update)

    @property
    def state(self):
        if getattr(self.coordinator, "_last_update", None) is None:
            return "unavailable"
        if time.time() - self.coordinator._last_update > MQTT_TIMEOUT:
            return "unavailable"

        device = self.coordinator.device
        if not device:
            return None
        data = device.get("Data", {})

        if self.key == "STATE":
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
        
                if SBF_OOF == 1 and SXF_ECO == 0 and SXF_AWA == 0 and SXF_TIME == 0:
                    return "AUTO"
                elif SBF_OOF == 1 and SXF_ECO == 1 and SXF_AWA == 0:
                    return "ECO"
                elif SBF_OOF == 1 and SXF_TIME == 1:
                    return "TIME"
                elif SBF_OOF == 1 and SXF_AWA == 1:
                    return "AWAY"
                elif SBF_OOF == 0:
                    return "OFF"
                else:
                    return "UNKNOWN"
            except Exception as e:
                _LOGGER.warning("Error analyzing operating mode: %s", e)
                return "UNKNOWN"

        if self.key == "ZM_AC_IN_PWR":
            try:
                amps = float(data.get("ZM_AC_IN_CUR", 0))
                volts = float(data.get("ZM_AC_IN_VOL", 230))
                return round(amps * volts, 2)
            except (TypeError, ValueError):
                return None

        if self.key == "ZM_AC_IN_ENERGY":
            try:
                amps = float(data.get("ZM_AC_IN_CUR", 0))
                volts = float(data.get("ZM_AC_IN_VOL", 230))
                power_w = amps * volts

                from homeassistant.util import dt as dt_util
                now = dt_util.utcnow()

                if self._last_energy_update is None:
                    self._last_energy_update = now
                    self._energy_kwh = 0.0
                    return round(self._energy_kwh, 4)

                elapsed_h = (now - self._last_energy_update).total_seconds() / 3600.0
                self._last_energy_update = now
                self._energy_kwh += (power_w * elapsed_h) / 1000.0

                return round(self._energy_kwh, 4)
            except Exception as e:
                _LOGGER.warning("Error calculating energy: %s", e)
                return None

        if getattr(self, "_attr_device_class", None) == "temperature":
            try:
                value = float(data.get(self.key, 0))
                if value > 149 or value < -50:
                    return "unknown"
                return round(value, 1)
            except (TypeError, ValueError):
                return "unknown"

        return data.get(self.key)

    @property
    def state_class(self):
        if self.key == "ZM_AC_IN_ENERGY":
            return "total_increasing"

        if self.key in {"STATE", "SW_VERSION", "MODE"}:
            return None

        return "measurement"

    @property
    def unit_of_measurement(self):
        return self._unit

    @callback
    def _handle_coordinator_update(self):
        if self.hass:
            self.hass.loop.call_soon_threadsafe(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        self.coordinator.async_remove_listener(self._handle_coordinator_update)