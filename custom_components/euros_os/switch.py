"""
===============================================================================
Euros OS Home Assistant Custom Integration
===============================================================================

File        : switch.py
Author      : Patryk "KoPcIu" Kopeć / https://github.com/McKoPcIu/EurosOS
Integration : euros_os
Version     : 0.1.1
Description : Custom integration for EurosEnergy and E-On devices.

===============================================================================
"""

import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback
from .const import DOMAIN, CONF_KEY, SWITCH_VARIABLES
from .coordinator import EurosOSMQTTCoordinator
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger("custom_components.euros_os")

async def async_setup_entry(hass, entry, async_add_entities):
    entry_data = hass.data[DOMAIN][entry.entry_id]["entry_data"]
    coordinator: EurosOSMQTTCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    device_info = hass.data[DOMAIN][entry.entry_id]["device_info"]

    entities = []
    unique_prefix = entry_data.get(CONF_KEY, "---")
    coordinator.entry_data = entry_data

    for key, info in SWITCH_VARIABLES.items():
        entities.append(EurosOSSwitch(coordinator, key, info, unique_prefix, device_info))

    async_add_entities(entities)
    _LOGGER.info("Added %d switch entities.", len(entities))

class EurosOSSwitch(SwitchEntity):
    def __init__(self, coordinator, key, info, unique_prefix, device_info):
        self.coordinator = coordinator
        self.key = key
        self._attr_name = info[0]
        self._attr_icon = info[1]
        self._attr_unique_id = f"{unique_prefix}_{key.lower()}"
        self._attr_device_info = device_info
        self._is_on = None

        coordinator.async_add_listener(self._handle_coordinator_update)

    @property
    def is_on(self):
        return self._is_on

    async def async_turn_on(self, **kwargs):
        entry_data = getattr(self.coordinator, "entry_data", {})
        device_data = getattr(self.coordinator.device, "get", lambda x, d=None: d)("Data", {})

        if self.key == "SWEXT_T_CWU":
            SBF_DHS = int(device_data.get("SBF_DHS", 0))
            SBF_DHX = int(device_data.get("SBF_DHX", 0))
            SBF_OOF = int(device_data.get("SBF_OOF", 0))
            SXF_ANL = int(device_data.get("SXF_ANL", 0))
            SBF_PHT = int(device_data.get("SBF_PHT", 0))

            if not (SBF_DHS == 1 and SBF_DHX == 1 and SBF_OOF == 1) or (SXF_ANL == 1 and SBF_PHT == 1):
                raise HomeAssistantError(
                    "Nie można włączyć CWU Turbo: warunki urządzenia nie są spełnione."
                )

        payload = {self.key: 1}
        success = await self.coordinator.async_set_device_value(payload, entry_data)
        if success:
            _LOGGER.debug("Value for %s updated to %s", self.key, 1)
            self._is_on = True
            self.async_write_ha_state()
        else:
            _LOGGER.error("Failed to update %s", self.key)

    async def async_turn_off(self, **kwargs):
        entry_data = getattr(self.coordinator, "entry_data", {})

        payload = {self.key: 0}
        success = await self.coordinator.async_set_device_value(payload, entry_data)
        if success:
            _LOGGER.debug("Value for %s updated to %s", self.key, 0)
            self._is_on = False
            self.async_write_ha_state()
        else:
            _LOGGER.error("Failed to update %s", self.key)

    @callback
    def _handle_coordinator_update(self):
        device_data = getattr(self.coordinator.device, "get", lambda x, d=None: d)("Data", {})

        self._is_on = int(device_data.get(self.key, 0)) == 1
        if self.hass:
            self.hass.loop.call_soon_threadsafe(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        self.coordinator.async_remove_listener(self._handle_coordinator_update)