"""
===============================================================================
Euros OS Home Assistant Custom Integration
===============================================================================

File        : select.py
Author      : Patryk "KoPcIu" Kopeć / https://github.com/McKoPcIu/EurosOS
Integration : euros_os
Version     : 0.1.0
Description : Custom integration for EurosEnergy and E-On devices.
              Provides SelectEntity entities for mode control via MQTT.

===============================================================================
"""

import logging
from homeassistant.components.select import SelectEntity
from homeassistant.core import callback
from .const import DOMAIN, CONF_KEY, SELECTS_VARIABLES
from .coordinator import EurosOSMQTTCoordinator

_LOGGER = logging.getLogger("custom_components.euros_os")


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up select entities from a config entry."""
    entry_data = hass.data[DOMAIN][entry.entry_id]["entry_data"]
    coordinator: EurosOSMQTTCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    device_info = hass.data[DOMAIN][entry.entry_id]["device_info"]

    entities = []
    unique_prefix = entry_data.get(CONF_KEY, "---")
    coordinator.entry_data = entry_data

    for key, info in SELECTS_VARIABLES.items():
        entities.append(EurosOSModeSelect(coordinator, key, info, unique_prefix, device_info))

    async_add_entities(entities)
    _LOGGER.info("Added %d select entities.", len(entities))


class EurosOSModeSelect(SelectEntity):

    def __init__(self, coordinator, key, info, unique_prefix, device_info):
        self.coordinator = coordinator
        self.key = key
        self._attr_name = info[0]
        self._unit = info[1]
        self._attr_icon = info[2]
        self._attr_options = info[3]
        self._attr_unique_id = f"{unique_prefix}_{key.lower()}"
        self._attr_device_info = device_info

        coordinator.async_add_listener(self._handle_coordinator_update)

    @property
    def unit_of_measurement(self):
        return self._unit

    @property
    def current_option(self):
        if not self.coordinator.device or "Data" not in self.coordinator.device:
            return None
        data = self.coordinator.device["Data"]
        return self._analyze_mode(data)

    async def async_select_option(self, option: str):
        entry_data = getattr(self.coordinator, "entry_data", {})
        payload = None

        if self.key == "MODE":
            # Mapowanie trybów pracy
            if option == "AUTO":
                payload = {
                    "SBF_OOF": 1,
                    "SXF_AWA": 0,
                    "SXF_ECO": 0,
                    "SXF_TIME": 0,
                }

            elif option == "ECO":
                payload = {
                    "SBF_OOF": 1,
                    "SXF_AWA": 0,
                    "SXF_ECO": 1,
                    "SXF_TIME": 0,
                }

            elif option == "AWAY":
                payload = {
                    "SBF_OOF": 1,
                    "SXF_AWA": 1,
                    "SXF_ECO": 0,
                    "SXF_TIME": 0,
                }

            elif option == "OFF":
                payload = {
                    "SBF_OOF": 0,
                    "SXF_AWA": 0,
                    "SXF_ECO": 0,
                    "SXF_TIME": 0,
                }

            elif option == "TIME":
                payload = {
                    "SBF_OOF": 1,
                    "SXF_AWA": 0,
                    "SXF_ECO": 0,
                    "SXF_TIME": 1,

                    "TWTSW_PN": 1, "TWTSW_WT": 1, "TWTSW_SR": 1, "TWTSW_CZ": 1,
                    "TWTSW_PT": 1, "TWTSW_SO": 1, "TWTSW_ND": 1,
                    "CWTSW_PN": 1, "CWTSW_WT": 1, "CWTSW_SR": 1, "CWTSW_CZ": 1,
                    "CWTSW_PT": 1, "CWTSW_SO": 1, "CWTSW_ND": 1,
                    "CWTSW_S1": 1, "CWTSW_S2": 1, "CWTSW_S3": 1,
                    "TWTSW_S1": 1, "TWTSW_S2": 1, "TWTSW_S3": 1,
                }

            else:
                _LOGGER.error("Unknown mode: %s", option)
                return

        else:
            payload = {self.key: option}

        success = await self.coordinator.async_set_device_value(payload, entry_data)
        if success:
            _LOGGER.debug("Mode updated to %s", option)
        else:
            _LOGGER.error("Failed to update mode to %s", option)

    @callback
    def _handle_coordinator_update(self):
        if self.hass:
            self.hass.loop.call_soon_threadsafe(self.async_write_ha_state)

    def _analyze_mode(self, data):
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
