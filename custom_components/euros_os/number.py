"""
===============================================================================
Euros OS Home Assistant Custom Integration
===============================================================================

File        : number.py
Author      : Patryk "KoPcIu" Kopeć / https://github.com/McKoPcIu/EurosOS
Integration : euros_os
Version     : 0.1.0
Description : Custom integration for EurosEnergy and E-On devices.

===============================================================================
"""

import logging
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import callback
from .const import DOMAIN, CONF_KEY, NUMBERS_VARIABLES
from .coordinator import EurosOSMQTTCoordinator

_LOGGER = logging.getLogger("custom_components.euros_os")

async def async_setup_entry(hass, entry, async_add_entities):
    entry_data = hass.data[DOMAIN][entry.entry_id]["entry_data"]
    coordinator: EurosOSMQTTCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    device_info = hass.data[DOMAIN][entry.entry_id]["device_info"]

    entities = []
    unique_prefix = entry_data.get(CONF_KEY, "---")
    coordinator.entry_data = entry_data

    for key, info in NUMBERS_VARIABLES.items():
        entities.append(EurosOSNumber(coordinator, key, info, unique_prefix, device_info))

    async_add_entities(entities)
    _LOGGER.info("Added %d writable number entities.", len(entities))

class EurosOSNumber(NumberEntity):
    def __init__(self, coordinator, key, info, unique_prefix, device_info):
        self.coordinator = coordinator
        self.key = key
        self._attr_name = info[0]
        self._unit = info[1] #self._attr_unit_of_measurement = info[1]
        self._attr_icon = info[2]
        self._attr_native_min_value = info[3]
        self._attr_native_max_value = info[4]
        self._attr_native_step = info[5]
        self._attr_native_value = None
        self._attr_unique_id = f"{unique_prefix}_{key.lower()}"
        self._attr_device_info = device_info

        if info[6] == "AUTO":
            self._attr_mode = NumberMode.AUTO
        elif info[6] == "SLIDER":
            self._attr_mode = NumberMode.SLIDER
        elif info[6] == "BOX":
            self._attr_mode = NumberMode.BOX

        coordinator.async_add_listener(self._handle_coordinator_update)

    async def async_set_native_value(self, value):
#        mode = self._get_device_mode()
#        if self.key in ("SX5", "SX6") and mode != "AUTO":
#            _LOGGER.warning("Cannot update %s: device mode is not AUTO (current: %s)", self.key, mode)
#            return

        entry_data = getattr(self.coordinator, "entry_data", {})

        payload = {self.key: value}
        success = await self.coordinator.async_set_device_value(payload, entry_data)
        if success:
            _LOGGER.debug("Value for %s updated to %s", self.key, value)
        else:
            _LOGGER.error("Failed to update %s", self.key)

    @property
    def unit_of_measurement(self):
        return self._unit

    @callback
    def _handle_coordinator_update(self):
        _LOGGER.debug("Value for %s is %s", self.key, self.coordinator.device.get("Data", {}).get(self.key))
        if self.coordinator.device and "Data" in self.coordinator.device:
            self._attr_native_value = self.coordinator.device["Data"].get(self.key)
        else:
            self._attr_native_value = None
        if self.hass:
            self.hass.loop.call_soon_threadsafe(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        self.coordinator.async_remove_listener(self._handle_coordinator_update)

"""
    def _get_device_mode(self):
        device_data = getattr(self.coordinator.device, "get", lambda x, d=None: d)("Data", {})
        try:
            SBF_OOF = int(device_data.get("SBF_OOF", 0))
            SXF_ECO = int(device_data.get("SXF_ECO", 0))
            SXF_AWA = int(device_data.get("SXF_AWA", 0))
            SXF_TIME = int(device_data.get("SXF_TIME", 0))

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
        except Exception:
            return "UNKNOWN"
"""