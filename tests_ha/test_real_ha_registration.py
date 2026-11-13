"""End-to-end local HA Core 2026.11 config-entry registration, without MQTT.

pytest-homeassistant provides an actual HomeAssistant instance. MQTT connect and
disconnect are replaced in the test before setup; the pump is never contacted.
"""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant.common import MockConfigEntry

from custom_components.euros_os.const import DOMAIN
from custom_components.euros_os.coordinator import EurosOSMQTTCoordinator


@pytest.mark.asyncio
async def test_real_ha_2026_11_registers_geo_and_ems_without_mqtt(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Euros OS (test fixture)",
        data={
            "key": "stage9-real-api",
            "ip": "127.0.0.1",
            "device_model": "GEO_1",
            "device_type": "FriskoGEO",
            "device_version": "1",
        },
    )
    entry.add_to_hass(hass)

    def fake_connect(self):
        self._closed = False
        self.connected.set()
        self.device = {
            "Name": "GEO_1",
            "Type": "FriskoGEO",
            "Data": {
                "TSM16": "23.5", "TSM13": "30.0", "T5fiz": "28.0",
                "T3fiz": "10.0", "T4fiz": "8.0",
                "VER_S1": 870, "VER_S2": 12,
                "SBF_DHS": 1, "SBF_DHX": 1, "SBF_OOF": 1,
                "SBB_QHW": 0, "SXF_TOE": 0, "SBB_QHT": 0, "SBB_QHL": 0,
                "SXF_ECO": 0, "SXF_AWA": 0, "SXF_TIME": 0,
                "U_ENE_TAR": 1,
            },
        }
        self._last_update = time.time()
        self.ems_meters = {
            "METER_1": {
                "TOTAL_ACT_POW_FL_1": "0.230",
                "POS_ACT_POW_FL_1": "15.53",
                "REW_ACT_POW_FL_1": "0.14",
            }
        }
        self._meter_last_update = {"METER_1": self._last_update}

    def fake_disconnect(self):
        self._closed = True
        self.connected.clear()

    with (
        patch.object(EurosOSMQTTCoordinator, "connect", fake_connect),
        patch.object(EurosOSMQTTCoordinator, "disconnect", fake_disconnect),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        device_registry = dr.async_get(hass)
        entity_registry = er.async_get(hass)
        # HA 2026.11 deprecates direct mapping access to registry.devices
        # and registry.entities. Use the public config-entry helpers instead.
        owned_devices = dr.async_entries_for_config_entry(
            device_registry, entry.entry_id
        )
        owned_entities = er.async_entries_for_config_entry(
            entity_registry, entry.entry_id
        )
        assert len(owned_devices) == 2
        assert len(owned_entities) == 73
        # HA entity registry uniqueness is (domain, platform, unique_id),
        # not unique_id alone: sensor and number may share a device key.
        assert len({
            (entity.domain, entity.platform, entity.unique_id)
            for entity in owned_entities
        }) == 73
        assert len({entity.unique_id for entity in owned_entities}) == 69

        pump = device_registry.async_get_device_by_identifier(
            (DOMAIN, "stage9-real-api"), entry.entry_id
        )
        meter = device_registry.async_get_device_by_identifier(
            (DOMAIN, "stage9-real-api_ems_meter_1"), entry.entry_id
        )
        assert pump is not None
        assert meter is not None
        assert meter.via_device_id == pump.id

        temperature = next(
            ent for ent in owned_entities
            if ent.unique_id == "stage9-real-api_tsm16"
        )
        assert temperature.entity_id.startswith("sensor.")
        assert hass.states.get(temperature.entity_id) is not None
        assert hass.states.get(temperature.entity_id).state == "23.5"

        # Capture the exact registry identity before unloading. Reload should
        # reactivate the same entities, not allocate "_2" suffixes or devices.
        identities_before = {
            (ent.domain, ent.platform, ent.unique_id): ent.entity_id
            for ent in owned_entities
        }
        device_ids_before = {device.id for device in owned_devices}
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.entry_id not in hass.data.get(DOMAIN, {})
        for entity in owned_entities:
            assert entity_registry.async_get(entity.entity_id) is not None

        # Repeat the full setup/unload cycle with the same ConfigEntry.
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        reload_entities = er.async_entries_for_config_entry(
            entity_registry, entry.entry_id
        )
        reload_devices = dr.async_entries_for_config_entry(
            device_registry, entry.entry_id
        )
        assert len(reload_entities) == 73
        assert len(reload_devices) == 2
        assert {
            (ent.domain, ent.platform, ent.unique_id): ent.entity_id
            for ent in reload_entities
        } == identities_before
        assert {device.id for device in reload_devices} == device_ids_before
        assert hass.states.get(temperature.entity_id).state == "23.5"

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.entry_id not in hass.data.get(DOMAIN, {})
        assert len(er.async_entries_for_config_entry(entity_registry, entry.entry_id)) == 73
