"""
===============================================================================
Euros OS Home Assistant Custom Integration
===============================================================================

File        : __init__.py
Author      : Patryk "KoPcIu" Kopeć / https://github.com/McKoPcIu/EurosOS
Integration : euros_os
Version     : 0.1.0
Description : Custom integration for EurosEnergy and E-On devices.

===============================================================================
"""

from homeassistant.core import HomeAssistant
from .const import DOMAIN, CONF_KEY, CONF_IP
from .coordinator import EurosOSMQTTCoordinator

PLATFORMS = ["sensor", "number", "select"]

async def async_setup(hass: HomeAssistant, config: dict):
    return True

async def async_setup_entry(hass, entry):
    hass.data.setdefault(DOMAIN, {})

    entry_data = entry.data.copy()
    topic = entry_data.get(CONF_KEY) + "/Dev"
    ip = entry_data.get(CONF_IP)
    coordinator = EurosOSMQTTCoordinator(ip, topic)
    
    await hass.async_add_executor_job(coordinator.connect)

    device_info = {
        "identifiers": {(DOMAIN, entry_data.get(CONF_KEY))},
        "name": entry_data.get(CONF_KEY),
        "manufacturer": "---",
        "model": entry_data.get("device_model", "---"),
    }

    hass.data[DOMAIN][entry.entry_id] = {
        "entry_data": entry_data,
        "coordinator": coordinator,
        "device_info": device_info
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass, entry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
