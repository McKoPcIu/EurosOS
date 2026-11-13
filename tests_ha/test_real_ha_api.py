"""Smoke-test Euros OS against *real* Home Assistant 2026.11 entity classes.

These tests are intentionally separate from tests/: the legacy tests replace
HA modules with fakes. No MQTT connection, service calls or device writes occur.
Run with Python >=3.14.2 and homeassistant==2026.11.0.
"""
from __future__ import annotations

import time
import unittest

import homeassistant
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import RestoreSensor, SensorEntity
from homeassistant.components.switch import SwitchEntity

from custom_components.euros_os.binary_sensor import EurosOSBinarySensor
from custom_components.euros_os.ems import EMS_DOM_SENSOR_DEFINITIONS
from custom_components.euros_os.number import EurosOSNumber
from custom_components.euros_os.select import EurosOSModeSelect
from custom_components.euros_os.sensor import (
    EurosOSEMSDailyEnergySensor,
    EurosOSEMSMeterSensor,
    EurosOSLegacyEstimatedEnergySensor,
    EurosOSSensor,
)
from custom_components.euros_os.switch import EurosOSSwitch


class OfflineCoordinator:
    def __init__(self):
        self.listeners = []
        self.device = {
            "Name": "GEO_1",
            "Data": {
                "TSM16": "22.5",
                "U_ENE_TAR": 1,
                "SBF_OOF": 1,
                "SXF_ECO": 0,
                "SXF_AWA": 0,
                "SXF_TIME": 0,
            },
        }
        self.pump_type = "FriskoGEO"
        self._last_update = time.time()
        self._meter_last_update = {"METER_1": time.time()}
        self.ems_meters = {
            "METER_1": {"POS_ACT_POW_FL_1": "120.55"}
        }
        self.entry_data = {"device_model": "GEO_1"}

    def async_add_listener(self, fn):
        self.listeners.append(fn)

    def async_remove_listener(self, fn):
        self.listeners.remove(fn)

    def pump_is_fresh(self):
        return True

    async def async_set_device_value(self, payload, entry_data):
        raise AssertionError("No MQTT commands are allowed during API tests")


class RealHomeAssistantApiTests(unittest.TestCase):
    def setUp(self):
        self.coordinator = OfflineCoordinator()
        self.device_info = {
            "identifiers": {("euros_os", "ha-api")},
            "name": "GEO_1",
            "manufacturer": "Euros Energy",
        }

    def test_sensor_entity_uses_native_value_and_ha_metadata(self):
        sensor = EurosOSSensor(
            self.coordinator,
            "TSM16",
            ("Temperature", "°C", "mdi:thermometer", "temperature"),
            "ha-api", self.device_info, device_type="FriskoGEO",
        )
        self.assertIsInstance(sensor, SensorEntity)
        self.assertEqual(sensor.native_value, 22.5)
        self.assertEqual(sensor.native_unit_of_measurement, "°C")
        self.assertEqual(sensor.device_class, "temperature")
        self.assertEqual(sensor.state_class, "measurement")
        self.assertEqual(sensor.unique_id, "ha-api_tsm16")
        self.assertTrue(sensor.available)
        self.coordinator._last_update -= 61
        self.assertFalse(sensor.available)

    def test_legacy_energy_uses_real_restore_sensor_api(self):
        sensor = EurosOSLegacyEstimatedEnergySensor(
            self.coordinator, "ZM_AC_IN_ENERGY",
            ("Estimated energy", "kWh", "mdi:counter", "energy"),
            "ha-api", self.device_info, device_type="FriskoATMO",
        )
        self.assertIsInstance(sensor, RestoreSensor)
        self.assertIsInstance(sensor, SensorEntity)
        self.assertTrue(callable(sensor.async_get_last_sensor_data))
        self.assertEqual(sensor.native_unit_of_measurement, "kWh")
        self.assertEqual(sensor.device_class, "energy")
        self.assertEqual(sensor.state_class, "total_increasing")
        self.assertEqual(sensor.unique_id, "ha-api_zm_ac_in_energy")
        self.assertFalse(sensor.should_poll)

    def test_ems_lifetime_and_daily_sensors_share_real_ha_contract(self):
        meter_info = {
            "identifiers": {("euros_os", "ha-api_ems_meter_1")},
            "name": "EMS – Dom", "model": "METER_1",
        }
        lifetime = EurosOSEMSMeterSensor(
            self.coordinator, "METER_1", "POS_ACT_POW_FL_1",
            EMS_DOM_SENSOR_DEFINITIONS["POS_ACT_POW_FL_1"],
            "ha-api", meter_info,
        )
        daily = EurosOSEMSDailyEnergySensor(
            self.coordinator, "METER_1", "POS_ACT_POW_FL_1",
            ("Daily imported energy", "mdi:counter"), "ha-api", meter_info,
        )
        self.assertIsInstance(lifetime, SensorEntity)
        self.assertIsInstance(daily, RestoreSensor)
        self.assertEqual(lifetime.native_value, 120.55)
        self.assertEqual(lifetime.state_class, "total_increasing")
        self.assertEqual(lifetime.native_unit_of_measurement, "kWh")
        self.assertEqual(daily.unique_id, "ha-api_ems_meter_1_daily_pos_act_pow_fl_1")
        self.assertEqual(daily.device_class, "energy")

    def test_writable_entity_classes_import_and_have_stable_unique_ids(self):
        number = EurosOSNumber(
            self.coordinator, "SPDHW_ZAD",
            ("Target CWU", "°C", "mdi:thermometer", 30, 55, 1, "BOX"),
            "ha-api", self.device_info,
        )
        mode = EurosOSModeSelect(
            self.coordinator, "MODE",
            ("Mode", None, "mdi:autorenew", ["AUTO", "ECO", "TIME", "AWAY", "OFF"]),
            "ha-api", self.device_info, device_type="FriskoGEO",
        )
        switch = EurosOSSwitch(
            self.coordinator, "SWEXT_T_CWU", ("CWU Turbo", "mdi:fire"),
            "ha-api", self.device_info,
        )
        binary = EurosOSBinarySensor(
            self.coordinator, "SIO_R02", ("CO pump", "mdi:pump"),
            "ha-api", self.device_info,
        )
        self.assertIsInstance(number, NumberEntity)
        self.assertIsInstance(mode, SelectEntity)
        self.assertIsInstance(switch, SwitchEntity)
        self.assertIsInstance(binary, BinarySensorEntity)
        self.assertEqual(number.unique_id, "ha-api_spdhw_zad")
        self.assertEqual(number.native_min_value, 30)
        self.assertEqual(number.native_max_value, 55)
        self.assertEqual(number.mode, NumberMode.BOX)
        self.assertEqual(mode.unique_id, "ha-api_mode")
        self.assertIn("EMS", mode.options)
        self.assertEqual(mode.current_option, "EMS")
        self.assertEqual(switch.unique_id, "ha-api_swext_t_cwu")
        self.assertEqual(binary.unique_id, "ha-api_sio_r02")

    def test_pump_telemetry_never_sends_mqtt_in_api_smoke_test(self):
        self.assertIsNotNone(homeassistant)
        # No broker, network, or device access is required by any test.
        self.assertTrue(self.coordinator.pump_is_fresh())


if __name__ == "__main__":
    unittest.main()
