"""
===============================================================================
Euros OS Home Assistant Custom Integration
===============================================================================

File        : __init__.py
Author      : Patryk "KoPcIu" Kopeć / https://github.com/McKoPcIu/EurosOS
Integration : euros_os
Version     : 0.1.1
Description : Custom integration for EurosEnergy and E-On devices.

===============================================================================
"""

from datetime import timedelta

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers import device_registry as dr
from .const import DOMAIN, CONF_KEY, CONF_IP
from .coordinator import EurosOSMQTTCoordinator
from .geo import GEO_DEVICE_TYPE, GEO_MANUFACTURER, geo_device_software_version

PLATFORMS = ["sensor", "number", "select", "switch", "binary_sensor"]

async def async_setup(hass: HomeAssistant, config: dict):
    return True

async def async_setup_entry(hass, entry):
    hass.data.setdefault(DOMAIN, {})

    entry_data = entry.data.copy()
    topic = entry_data.get(CONF_KEY) + "/Dev"
    ip = entry_data.get(CONF_IP)
    coordinator = EurosOSMQTTCoordinator(
        ip, topic,
        pump_name=entry_data.get("device_model"),
        pump_type=entry_data.get("device_type"),
        event_loop=hass.loop,
    )
    
    try:
        await hass.async_add_executor_job(coordinator.connect)
    except ConnectionError as exc:
        raise ConfigEntryNotReady("Euros OS MQTT connection unavailable") from exc

    is_geo = entry_data.get("device_type") == GEO_DEVICE_TYPE
    device_info = {
        "identifiers": {(DOMAIN, entry_data.get(CONF_KEY))},
        "name": entry_data.get(CONF_KEY),
        "manufacturer": GEO_MANUFACTURER if is_geo else "---",
        "model": entry_data.get("device_model", "---"),
    }
    if is_geo:
        version = geo_device_software_version(coordinator.device)
        if version is not None:
            device_info["sw_version"] = version

    hass.data[DOMAIN][entry.entry_id] = {
        "entry_data": entry_data,
        "coordinator": coordinator,
        "device_info": device_info
    }

    if is_geo:
        @callback
        def _async_update_geo_device_info():
            """Keep the HA device metadata in sync with live GEO MQTT data."""
            device_registry = dr.async_get(hass)
            device = device_registry.async_get_device_by_identifier(
                (DOMAIN, entry_data.get(CONF_KEY)), entry.entry_id
            )
            if device is None:
                return

            changes = {}
            if device.manufacturer != GEO_MANUFACTURER:
                changes["manufacturer"] = GEO_MANUFACTURER
            version = geo_device_software_version(coordinator.device)
            if version is not None and device.sw_version != version:
                changes["sw_version"] = version
            if changes:
                device_registry.async_update_device(device.id, **changes)

        def _on_mqtt_update():
            # The MQTT callback runs outside the Home Assistant event loop.
            hass.loop.call_soon_threadsafe(_async_update_geo_device_info)

        coordinator.async_add_listener(_on_mqtt_update)
        hass.data[DOMAIN][entry.entry_id]["metadata_listener"] = _on_mqtt_update

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    if is_geo:
        # Also handle packets received before the listener was registered.
        _async_update_geo_device_info()

    @callback
    def _check_mqtt_staleness(_now):
        # A silent broker cannot initiate its own unavailable state update.
        # The coordinator notifies only on an actual freshness transition.
        coordinator.check_stale()

    hass.data[DOMAIN][entry.entry_id]["watchdog_unsub"] = (
        async_track_time_interval(
            hass, _check_mqtt_staleness, timedelta(seconds=10)
        )
    )
    return True

async def async_unload_entry(hass, entry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry_state = hass.data[DOMAIN].pop(entry.entry_id, None)
        if entry_state:
            coordinator = entry_state["coordinator"]
            watchdog_unsub = entry_state.get("watchdog_unsub")
            if watchdog_unsub:
                watchdog_unsub()
            for name in ("metadata_listener", "meter_discovery_listener"):
                if listener := entry_state.get(name):
                    coordinator.async_remove_listener(listener)
            # Do not leave a Paho MQTT worker running after unloading/reloading.
            await hass.async_add_executor_job(coordinator.disconnect)
    return unload_ok
