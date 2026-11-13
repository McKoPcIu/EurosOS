"""Stage 7 read-only MQTT -> HA sensor-platform integration simulations.

This runs the real Euros OS coordinator, EMS parser and sensor platform with
minimal Home Assistant and Paho stubs. It does NOT connect to an MQTT broker,
execute pump controls, or claim to be a full Home Assistant runtime test.
"""
import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

from test_coordinator_discovery import FakeClient, FakeLoop
from test_dynamic_ems import FakeRestoreSensor

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "euros_os"


def mod(name, **props):
    result = types.ModuleType(name)
    result.__dict__.update(props)
    return result


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


class SimpleSensor:
    hass = None

    def async_write_ha_state(self):
        self._writes = getattr(self, "_writes", 0) + 1


class Registry:
    def __init__(self):
        self.calls = []

    def async_get_or_create(self, **kwargs):
        self.calls.append(kwargs)
        return types.SimpleNamespace(id="parent-device-id")


class RealCoordinatorToHaPlatformTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = Registry()
        cls.patch_modules = patch.dict(sys.modules, {
            "homeassistant": mod("homeassistant"),
            "homeassistant.core": mod("homeassistant.core", callback=lambda fn: fn),
            "homeassistant.helpers": mod("homeassistant.helpers"),
            "homeassistant.helpers.update_coordinator": mod(
                "homeassistant.helpers.update_coordinator",
                DataUpdateCoordinator=type("DataUpdateCoordinator", (), {
                    "__init__": lambda self, *args, **kwargs: None,
                }),
            ),
            "homeassistant.helpers.device_registry": mod(
                "homeassistant.helpers.device_registry",
                async_get=lambda hass: cls.registry,
            ),
            "homeassistant.helpers.entity": mod(
                "homeassistant.helpers.entity",
                EntityCategory=types.SimpleNamespace(DIAGNOSTIC="diagnostic"),
            ),
            "homeassistant.helpers.event": mod(
                "homeassistant.helpers.event",
                async_track_time_change=lambda *args, **kwargs: lambda: None,
            ),
            "homeassistant.components": mod("homeassistant.components"),
            "homeassistant.components.sensor": mod(
                "homeassistant.components.sensor",
                SensorEntity=SimpleSensor,
                RestoreSensor=FakeRestoreSensor,
            ),
            "homeassistant.util": mod("homeassistant.util"),
            "homeassistant.util.dt": mod("homeassistant.util.dt",
                now=lambda: __import__("datetime").datetime(2026, 11, 9)),
            "paho": mod("paho"),
            "paho.mqtt": mod("paho.mqtt"),
            "paho.mqtt.client": mod("paho.mqtt.client", Client=FakeClient),
            "custom_components": mod("custom_components"),
            "custom_components.euros_os": mod("custom_components.euros_os"),
            "custom_components.euros_os.const": mod(
                "custom_components.euros_os.const",
                DOMAIN="euros_os", CONF_KEY="key", CONF_IP="ip",
                SENSORS_VARIABLES={"TSM16": ("Ground temp", "°C", "mdi:thermometer", "temperature")},
                MQTT_TIMEOUT=60, MQTT_PORT=8883,
                MQTT_USER="test", MQTT_PASSWORD="test",
            ),
            "custom_components.euros_os.geo": mod(
                "custom_components.euros_os.geo",
                GEO_DEVICE_TYPE="FriskoGEO",
                GEO_GROUND_SOURCE_DELTA_T="geo_ground_delta",
                GEO_GROUND_SOURCE_DELTA_T_NAME="Ground delta",
                GEO_UPPER_SOURCE_DELTA_T="geo_upper_delta",
                GEO_UPPER_SOURCE_DELTA_T_NAME="Upper delta",
                calculate_ground_source_delta_t=lambda *args: None,
                calculate_upper_source_delta_t=lambda *args: None,
                calculate_geo_operating_state=lambda *args: None,
                entity_supported_for_device=lambda *args: True,
                sensor_info_for_device=lambda key, info, device_type: info,
            ),
        })
        cls.patch_modules.start()
        load("custom_components.euros_os.discovery", "discovery.py")
        load("custom_components.euros_os.ems", "ems.py")
        cls.coordinator_module = load("custom_components.euros_os.coordinator", "coordinator.py")
        cls.sensor_module = load("custom_components.euros_os.sensor", "sensor.py")

    @classmethod
    def tearDownClass(cls):
        cls.patch_modules.stop()

    def setUp(self):
        FakeClient.instances.clear()
        self.registry.calls.clear()
        self.loop = FakeLoop()
        self.batches = []
        self.created = []
        self.coordinator = None
        self.hass = None
        self.client = None

    def setup_integration(self, name="GEO_1", pump_type="FriskoGEO"):
        self.coordinator = self.coordinator_module.EurosOSMQTTCoordinator(
            "127.0.0.1", "site/Dev",
            pump_name=name, pump_type=pump_type, event_loop=self.loop,
        )
        self.coordinator.connect()
        self.client = FakeClient.instances[-1]
        entry_state = {
            "entry_data": {"key": "site", "device_type": pump_type},
            "coordinator": self.coordinator,
            "device_info": {"identifiers": {("euros_os", "site")}, "name": "site"},
        }
        self.hass = types.SimpleNamespace(
            loop=self.loop, data={"euros_os": {"entry": entry_state}},
        )

        def add_entities(entities):
            for entity in entities:
                entity.hass = self.hass
                self.created.append(entity)
            self.batches.append(entities)

        asyncio.run(self.sensor_module.async_setup_entry(
            self.hass, types.SimpleNamespace(entry_id="entry"), add_entities,
        ))

    def sensor(self, uid):
        return next(e for e in self.created if e._attr_unique_id == uid)

    @staticmethod
    def pump(name="GEO_1", typ="FriskoGEO", temperature="24.2"):
        return {"Name": name, "Type": typ, "Data": {"TSM16": temperature}}

    @staticmethod
    def meter(name="METER_1", power="0.168"):
        return {"Name": name, "Type": "METER",
                "Data": {"TOTAL_ACT_POW_FL_1": power, "POS_ACT_POW_FL_1": "319.37"}}

    def test_full_geo_packet_routes_to_both_pump_and_legacy_ems(self):
        self.setup_integration()
        self.assertFalse(self.sensor("site_tsm16").available)
        self.assertIsNone(self.sensor("site_tsm16").native_value)
        self.client.emit([self.meter(), self.pump()])
        self.loop.flush()
        self.assertEqual(self.sensor("site_tsm16").native_value, 24.2)
        self.assertEqual(self.sensor("site_ems_meter_1_total_act_pow_fl_1").native_value, 0.168)
        self.assertEqual(self.sensor("site_ems_meter_1_total_act_pow_fl_1").available, True)
        self.assertEqual(sum(getattr(e, "meter_name", None) == "METER_1" for e in self.created), 35)
        self.assertEqual(self.client.published, [])

    def test_new_meter_only_packet_discovers_entity_without_refreshing_pump(self):
        self.setup_integration()
        self.client.emit([self.pump(), self.meter()])
        self.loop.flush()
        pump_updated_at = self.coordinator._last_update
        self.client.emit([self.meter("METER_2", "-0.125")])
        self.loop.flush()
        self.assertEqual(self.coordinator._last_update, pump_updated_at)
        new = self.sensor("site_ems_meter_2_total_act_pow_fl_1")
        self.assertEqual(new.native_value, -0.125)
        self.assertEqual(new._attr_device_info["model"], "METER_2")
        count = len(self.created)
        self.client.emit([self.meter("METER_2", "-0.200")])
        self.loop.flush()
        self.assertEqual(len(self.created), count)
        self.assertEqual(new.native_value, -0.2)
        self.assertEqual(self.client.published, [])

    def test_allinone_without_meter_does_not_register_ems(self):
        self.setup_integration("ALLINONE_1", "FriskoALLINONE")
        self.client.emit([self.pump("ALLINONE_1", "FriskoALLINONE")])
        self.loop.flush()
        self.assertEqual(self.sensor("site_tsm16").native_value, 24.2)
        self.assertFalse(any(hasattr(e, "meter_name") for e in self.created))
        self.assertFalse(self.registry.calls)
        self.assertEqual(self.client.published, [])

    def test_outage_and_corruption_do_not_delete_entities_or_change_history_ids(self):
        self.setup_integration()
        self.client.emit([self.pump(), self.meter()])
        self.loop.flush()
        ids = {e._attr_unique_id for e in self.created}
        self.client.emit_raw(b'{"Devices":null}')
        self.client.emit_raw(b'{"Devices":[{"Name":"GEO_1","Type":"FriskoGEO","Data":null}]}')
        self.loop.flush()
        self.assertEqual({e._attr_unique_id for e in self.created}, ids)
        self.assertEqual(self.sensor("site_ems_meter_1_total_act_pow_fl_1").native_value, 0.168)
        self.coordinator.disconnect()
        self.client.emit([self.pump(), self.meter(power="999")])
        self.loop.flush()
        self.assertEqual({e._attr_unique_id for e in self.created}, ids)
        self.assertEqual(self.sensor("site_ems_meter_1_total_act_pow_fl_1").native_value, 0.168)
        self.assertEqual(self.client.published, [])


if __name__ == "__main__":
    unittest.main()
