"""
===============================================================================
Euros OS Home Assistant Custom Integration
===============================================================================

File        : binary_sensor.py
Author      : Patryk "KoPcIu" Kopeć / https://github.com/McKoPcIu/EurosOS
Integration : euros_os
Version     : 0.1.1
Description : Custom integration for EurosEnergy and E-On devices.

===============================================================================
"""

import logging
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import callback
from .const import DOMAIN, CONF_KEY, BINARY_SENSOR_VARIABLES
from .coordinator import EurosOSMQTTCoordinator

_LOGGER = logging.getLogger("custom_components.euros_os")

async def async_setup_entry(hass, entry, async_add_entities):
    entry_data = hass.data[DOMAIN][entry.entry_id]["entry_data"]
    coordinator: EurosOSMQTTCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    device_info = hass.data[DOMAIN][entry.entry_id]["device_info"]

    entities = []
    unique_prefix = entry_data.get(CONF_KEY, "---")
    coordinator.entry_data = entry_data

    for key, info in BINARY_SENSOR_VARIABLES.items():
        entities.append(EurosOSBinarySensor(coordinator, key, info, unique_prefix, device_info))

    async_add_entities(entities)
    _LOGGER.info("Added %d binary_sensor entities.", len(entities))


class EurosOSBinarySensor(BinarySensorEntity):
    def __init__(self, coordinator, key, info, unique_prefix, device_info):
        self.coordinator = coordinator
        self.key = key
        self._attr_name = info[0]
        self._attr_icon = info[1]
        self._attr_unique_id = f"{unique_prefix}_{key.lower()}"
        self._attr_device_info = device_info
        self._attr_is_on = None

        coordinator.async_add_listener(self._handle_coordinator_update)

    @callback
    def _handle_coordinator_update(self):
        device_data = getattr(self.coordinator.device, "get", lambda x, d=None: d)("Data", {})

        if self.key in ["SIO_R11", "SIO_R01"] and device_data.get("SWEXT_ZBCRO", 0) == 0:
            return

        self._attr_is_on = int(device_data.get(self.key, 0)) == 1
        if self.hass:
            self.hass.loop.call_soon_threadsafe(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        self.coordinator.async_remove_listener(self._handle_coordinator_update)