"""Stage 5: dynamic METER_N discovery without a broker or real Home Assistant."""
import asyncio
from datetime import datetime
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "euros_os"


def mod(name, **fields):
    result = types.ModuleType(name)
    result.__dict__.update(fields)
    return result


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


class EmsHelperDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ems = load("test_stage5_ems_helpers", "ems.py")

    def test_meter_one_keeps_all_existing_keys_and_names(self):
        ems = self.ems
        valid_meter = {"TOTAL_ACT_POW_FL_1": "0.025"}
        self.assertEqual(len(ems.discover_ems_sensor_keys("METER_1", valid_meter)), 33)
        self.assertEqual(len(ems.discover_ems_daily_keys("METER_1", valid_meter)), 2)
        self.assertEqual(ems.discover_ems_sensor_keys("METER_1", {}), ())
        self.assertEqual(ems.discover_ems_daily_keys("METER_1", {}), ())
        self.assertEqual(ems.ems_meter_device_name("METER_1"), "EMS – Dom")
        self.assertEqual(ems.ems_meter_sensor_info(
            "METER_1", "TOTAL_ACT_POW_FL_1"), ems.EMS_DOM_SENSOR_DEFINITIONS["TOTAL_ACT_POW_FL_1"])

    def test_second_meter_only_valid_reported_fields(self):
        ems = self.ems
        keys = ems.discover_ems_sensor_keys("METER_2", {
            "TOTAL_ACT_POW_FL_1": "0.125",
            "A_PHA_VOLT_FL_1": "invalid",
            "POS_ACT_POW_FL_1": None,
            "NOT_SUPPORTED": 10,
        })
        self.assertEqual(keys, ("TOTAL_ACT_POW_FL_1",))
        self.assertEqual(ems.discover_ems_daily_keys("METER_2", {"POS_ACT_POW_FL_1": 20}), ())
        self.assertEqual(ems.ems_meter_device_name("METER_2"), "EMS – METER_2")
        self.assertEqual(ems.ems_meter_sensor_info("METER_2", "TOTAL_ACT_POW_FL_1")[0],
                         "EMS – METER_2 – TOTAL_ACT_POW_FL_1")

    def test_invalid_reading_is_not_zero(self):
        self.assertEqual(self.ems.discover_ems_sensor_keys("METER_3", {"TOTAL_ACT_POW_FL_1": ""}), ())
        self.assertEqual(self.ems.discover_ems_sensor_keys("METER_3", {"TOTAL_ACT_POW_FL_1": "0"}), ("TOTAL_ACT_POW_FL_1",))


class FakeRestoreSensor:
    """Minimal HA RestoreSensor behavior used by daily-counter integration tests."""
    hass = None

    async def async_added_to_hass(self):
        pass

    async def async_get_last_state(self):
        return getattr(self, "_restored_state", None)

    async def async_get_last_sensor_data(self):
        return getattr(self, "_restored_sensor_data", None)

    def async_on_remove(self, cleanup):
        self._test_cleanup = cleanup

    def async_write_ha_state(self):
        self._test_writes = getattr(self, "_test_writes", 0) + 1

    @property
    def native_value(self):
        return self._attr_native_value


class FakeCoordinator:
    def __init__(self):
        self.ems_meters = {}
        self._meter_last_update = {}
        self.listeners = []
        self.device = {}
        self._last_update = None

    def async_add_listener(self, listener):
        self.listeners.append(listener)

    def async_remove_listener(self, listener):
        self.listeners.remove(listener)

    def emit(self):
        for listener in tuple(self.listeners):
            listener()


class Registry:
    def __init__(self):
        self.calls = []

    def async_get_or_create(self, **kwargs):
        self.calls.append(kwargs)
        return types.SimpleNamespace(id="pump_registry_id")


class DynamicEmsPlatformTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = Registry()
        fake_emsc = mod("custom_components.euros_os.ems")
        cls.patch_modules = patch.dict(sys.modules, {
            "homeassistant": mod("homeassistant"),
            "homeassistant.components": mod("homeassistant.components"),
            "homeassistant.components.sensor": mod("homeassistant.components.sensor",
                SensorEntity=type("SensorEntity", (), {"hass": None}),
                RestoreSensor=FakeRestoreSensor),
            "homeassistant.helpers": mod("homeassistant.helpers"),
            "homeassistant.helpers.device_registry": mod(
                "homeassistant.helpers.device_registry", async_get=lambda hass: cls.registry),
            "homeassistant.helpers.entity": mod("homeassistant.helpers.entity",
                EntityCategory=types.SimpleNamespace(DIAGNOSTIC="diagnostic")),
            "homeassistant.helpers.event": mod("homeassistant.helpers.event",
                async_track_time_change=lambda *args, **kwargs: lambda: None),
            "homeassistant.util": mod("homeassistant.util"),
            "homeassistant.util.dt": mod("homeassistant.util.dt",
                now=lambda: datetime(2026, 11, 9)),
            "homeassistant.core": mod("homeassistant.core", callback=lambda fn: fn),
            "custom_components": mod("custom_components"),
            "custom_components.euros_os": mod("custom_components.euros_os"),
            "custom_components.euros_os.const": mod(
                "custom_components.euros_os.const",
                DOMAIN="euros_os", CONF_KEY="key", CONF_IP="ip",
                SENSORS_VARIABLES={}, MQTT_TIMEOUT=60),
            "custom_components.euros_os.coordinator": mod(
                "custom_components.euros_os.coordinator",
                EurosOSMQTTCoordinator=FakeCoordinator),
            "custom_components.euros_os.geo": mod(
                "custom_components.euros_os.geo",
                GEO_DEVICE_TYPE="FriskoGEO",
                GEO_GROUND_SOURCE_DELTA_T="GEO_DELTA_1",
                GEO_GROUND_SOURCE_DELTA_T_NAME="Delta 1",
                GEO_UPPER_SOURCE_DELTA_T="GEO_DELTA_2",
                GEO_UPPER_SOURCE_DELTA_T_NAME="Delta 2",
                calculate_ground_source_delta_t=lambda *args: None,
                calculate_upper_source_delta_t=lambda *args: None,
                calculate_geo_operating_state=lambda *args: None,
                entity_supported_for_device=lambda *args: True,
                sensor_info_for_device=lambda key, info, device_type: info),
        })
        cls.patch_modules.start()
        load("custom_components.euros_os.ems", "ems.py")
        cls.sensor = load("custom_components.euros_os.sensor", "sensor.py")

    @classmethod
    def tearDownClass(cls):
        cls.patch_modules.stop()

    def setUp(self):
        self.registry.calls.clear()
        self.coordinator = FakeCoordinator()
        self.entry = types.SimpleNamespace(entry_id="entry")
        self.state = {
            "entry_data": {"key": "abcdef", "device_type": "FriskoALLINONE"},
            "coordinator": self.coordinator,
            "device_info": {"identifiers": {("euros_os", "abcdef")}, "name": "pump"},
        }
        self.hass = types.SimpleNamespace(data={"euros_os": {"entry": self.state}})
        self.batches = []

    def setup_platform(self, pump_type="FriskoALLINONE"):
        self.state["entry_data"]["device_type"] = pump_type
        asyncio.run(self.sensor.async_setup_entry(
            self.hass, self.entry, lambda entities: self.batches.append(entities)
        ))

    def test_legacy_energy_platform_preserves_id_and_geo_exclusion(self):
        # A legacy key remains the same entity, despite the RestoreSensor class.
        definitions = {"ZM_AC_IN_ENERGY": ("Energia całkowita", "kWh", "mdi:counter", "energy")}
        with patch.dict(self.sensor.SENSORS_VARIABLES, definitions, clear=True):
            self.setup_platform("FriskoATMO")
            energy = next(e for e in self.batches[0]
                          if getattr(e, "key", None) == "ZM_AC_IN_ENERGY")
            self.assertIsInstance(energy, self.sensor.EurosOSLegacyEstimatedEnergySensor)
            self.assertEqual(energy._attr_unique_id, "abcdef_zm_ac_in_energy")
            self.assertEqual(energy._attr_native_unit_of_measurement, "kWh")
            self.assertEqual(energy._attr_state_class, "total_increasing")
            self.assertEqual(energy._attr_should_poll, False)
        # On GEO the model filter excludes the unverified pump energy sensor.
        self.assertIn("ZM_AC_IN_ENERGY", (ROOT / "geo.py").read_text(encoding="utf-8"))

    def test_allinone_without_meter_has_no_ems_and_no_fake_device(self):
        self.setup_platform()
        self.assertEqual(self.batches, [[]])
        self.assertEqual(self.registry.calls, [])
        self.assertEqual(len(self.coordinator.listeners), 1)

    def test_meters_appear_dynamically_without_restart_or_duplicates(self):
        self.setup_platform()
        self.coordinator.ems_meters = {"METER_2": {"TOTAL_ACT_POW_FL_1": "0.05"}}
        self.coordinator.emit()
        self.assertEqual(len(self.batches[-1]), 1)
        entity = self.batches[-1][0]
        self.assertEqual(entity._attr_unique_id, "abcdef_ems_meter_2_total_act_pow_fl_1")
        self.assertEqual(entity._attr_device_info["identifiers"], {("euros_os", "abcdef_ems_meter_2")})
        self.assertEqual(entity._attr_device_info["via_device_id"], "pump_registry_id")
        self.coordinator.emit()
        self.assertEqual(len(self.batches), 2)
        self.coordinator.ems_meters["METER_2"]["A_PHA_VOLT_FL_1"] = "231.2"
        self.coordinator.emit()
        self.assertEqual(len(self.batches), 3)
        self.assertEqual(self.batches[-1][0]._attr_unique_id,
                         "abcdef_ems_meter_2_a_pha_volt_fl_1")
        self.assertEqual(len(self.registry.calls), 1)

    def test_meter_one_retains_legacy_ids_and_daily_sensors(self):
        self.coordinator.ems_meters = {"METER_1": {"TOTAL_ACT_POW_FL_1": "0.025"}}
        self.setup_platform("FriskoGEO")
        ems_entities = [entity for entity in self.batches[0]
                        if getattr(entity, "meter_name", None) == "METER_1"]
        self.assertEqual(len(ems_entities), 35)
        ids = {entity._attr_unique_id for entity in ems_entities}
        self.assertIn("abcdef_ems_meter_1_total_act_pow_fl_1", ids)
        self.assertIn("abcdef_ems_meter_1_daily_pos_act_pow_fl_1", ids)
        self.assertEqual(ems_entities[0]._attr_device_info["name"], "EMS – Dom")

    def test_meter_temporarily_missing_does_not_remove_registered_entities(self):
        self.setup_platform()
        self.coordinator.ems_meters = {"METER_3": {"TOTAL_ACT_POW_FL_1": 1.0}}
        self.coordinator.emit()
        count = len(self.batches)
        self.coordinator.ems_meters = {}
        self.coordinator.emit()
        self.assertEqual(len(self.batches), count)
        self.coordinator.ems_meters = {"METER_3": {"TOTAL_ACT_POW_FL_1": 2.0}}
        self.coordinator.emit()
        self.assertEqual(len(self.batches), count)

    def test_reloading_platform_reuses_legacy_unique_ids(self):
        # A new coordinator and fresh entities use the same unique IDs, so
        # HA's entity registry can reuse historic METER_1 entities/history.
        self.coordinator.ems_meters = {
            "METER_1": {"TOTAL_ACT_POW_FL_1": "0.100"}
        }
        self.setup_platform("FriskoGEO")
        first = {
            entity._attr_unique_id
            for entity in self.batches[0]
            if getattr(entity, "meter_name", None) == "METER_1"
        }
        self.assertEqual(len(first), 35)
        self.coordinator = FakeCoordinator()
        self.coordinator.ems_meters = {
            "METER_1": {"TOTAL_ACT_POW_FL_1": "0.200"}
        }
        self.state["coordinator"] = self.coordinator
        self.setup_platform("FriskoGEO")
        second = {
            entity._attr_unique_id
            for entity in self.batches[-1]
            if getattr(entity, "meter_name", None) == "METER_1"
        }
        self.assertEqual(first, second)
        self.assertIn("abcdef_ems_meter_1_daily_rew_act_pow_fl_1", second)

    def test_reloading_platform_reuses_additional_meter_unique_ids(self):
        self.coordinator.ems_meters = {
            "METER_2": {"TOTAL_ACT_POW_FL_1": "0.100"}
        }
        self.setup_platform()
        first = [
            entity._attr_unique_id for entity in self.batches[0]
            if getattr(entity, "meter_name", None) == "METER_2"
        ]
        self.coordinator = FakeCoordinator()
        self.coordinator.ems_meters = {
            "METER_2": {"TOTAL_ACT_POW_FL_1": "0.200"}
        }
        self.state["coordinator"] = self.coordinator
        self.setup_platform()
        second = [
            entity._attr_unique_id for entity in self.batches[-1]
            if getattr(entity, "meter_name", None) == "METER_2"
        ]
        self.assertEqual(first, second)
        self.assertEqual(first, ["abcdef_ems_meter_2_total_act_pow_fl_1"])

    def test_missing_pump_temperature_is_unknown_not_zero(self):
        import time
        self.coordinator.device = {
            "Name": "GEO_1", "Type": "FriskoGEO", "Data": {}
        }
        self.coordinator._last_update = time.time()
        sensor = self.sensor.EurosOSSensor(
            self.coordinator, "TSM16",
            ("Temperature", "°C", "mdi:thermometer", "temperature"),
            "abcdef", self.state["device_info"], device_type="FriskoGEO",
        )
        self.assertIsNone(sensor.native_value)
        for raw in ("NaN", "inf", "broken", None):
            with self.subTest(raw=raw):
                self.coordinator.device["Data"] = {"TSM16": raw}
                self.assertIsNone(sensor.native_value)
        self.coordinator.device["Data"] = {"TSM16": "0"}
        self.assertEqual(sensor.native_value, 0.0)
        self.coordinator.device["Data"] = {"TSM16": "24.26"}
        self.assertEqual(sensor.native_value, 24.3)

    def test_malformed_meter_reading_becomes_unavailable_not_zero(self):
        self.setup_platform()
        self.coordinator.ems_meters = {
            "METER_2": {"TOTAL_ACT_POW_FL_1": "-0.125"}
        }
        self.coordinator.emit()
        entity = self.batches[-1][0]
        import time
        self.coordinator._meter_last_update["METER_2"] = time.time()
        self.assertEqual(entity.native_value, -0.125)
        self.assertTrue(entity.available)
        count = len(self.batches)

        for malformed in (None, "NaN", "inf", "", "broken", True):
            with self.subTest(value=malformed):
                self.coordinator.ems_meters = {
                    "METER_2": {"TOTAL_ACT_POW_FL_1": malformed}
                }
                self.coordinator.emit()
                self.assertIsNone(entity.native_value)
                self.assertFalse(entity.available)
                self.assertEqual(len(self.batches), count)
                self.assertEqual(
                    entity._attr_unique_id, "abcdef_ems_meter_2_total_act_pow_fl_1"
                )
        self.coordinator.ems_meters = {
            "METER_2": {"TOTAL_ACT_POW_FL_1": "0"}
        }
        self.coordinator.emit()
        self.assertEqual(entity.native_value, 0.0)
        self.assertTrue(entity.available)

    def test_multiple_meters_have_distinct_ids_and_no_inferred_daily_totals(self):
        self.coordinator.ems_meters = {
            "METER_2": {"TOTAL_ACT_POW_FL_1": "0.1"},
            "METER_3": {"A_PHA_VOLT_FL_1": "231.2"},
        }
        self.setup_platform()
        entities = self.batches[0]
        self.assertEqual(len(entities), 2)
        self.assertEqual(len({e._attr_unique_id for e in entities}), 2)
        self.assertEqual({e.meter_name for e in entities}, {"METER_2", "METER_3"})
        self.assertFalse(any("_daily_" in e._attr_unique_id for e in entities))
        self.assertEqual(len(self.registry.calls), 1)

    def test_daily_counter_restores_valid_state_and_ignores_invalid_packet(self):
        self.coordinator.ems_meters = {
            "METER_1": {
                "TOTAL_ACT_POW_FL_1": "0.12",
                "POS_ACT_POW_FL_1": "319.37",
                "REW_ACT_POW_FL_1": "100.00",
            }
        }
        self.setup_platform("FriskoGEO")
        daily = next(e for e in self.batches[0]
                     if getattr(e, "meter_name", None) == "METER_1"
                     and getattr(e, "key", None) == "POS_ACT_POW_FL_1"
                     and "_daily_" in e._attr_unique_id)
        daily.hass = self.hass
        daily._restored_state = types.SimpleNamespace(
            state="1.23",
            attributes={"ems_day": "2026-11-09", "last_meter_kwh": "319.28"},
        )
        import time
        self.coordinator._meter_last_update["METER_1"] = time.time()
        asyncio.run(daily.async_added_to_hass())
        self.assertAlmostEqual(daily.native_value, 1.32)
        self.assertEqual(daily.extra_state_attributes["last_meter_kwh"], 319.37)
        self.assertTrue(daily.available)

        # Data continuity: a transient bad kWh reading must not reset the
        # accumulated daily consumption or inject a synthetic 0.
        self.coordinator.ems_meters = {
            "METER_1": {"POS_ACT_POW_FL_1": "NaN"}
        }
        daily._refresh_from_meter()
        self.assertAlmostEqual(daily.native_value, 1.32)
        self.assertFalse(daily.available)

        self.coordinator.ems_meters = {
            "METER_1": {"POS_ACT_POW_FL_1": "319.40"}
        }
        daily._refresh_from_meter()
        self.assertAlmostEqual(daily.native_value, 1.35)
        self.assertTrue(daily.available)

    def test_invalid_restored_state_is_not_accepted_as_daily_total(self):
        self.coordinator.ems_meters = {
            "METER_1": {"TOTAL_ACT_POW_FL_1": "0.5", "POS_ACT_POW_FL_1": "broken"}
        }
        self.setup_platform("FriskoGEO")
        daily = next(e for e in self.batches[0]
                     if getattr(e, "meter_name", None) == "METER_1"
                     and "_daily_pos_act_pow_fl_1" in e._attr_unique_id)
        daily.hass = self.hass
        daily._restored_state = types.SimpleNamespace(
            state="NaN", attributes={"ems_day": "2026-11-09", "last_meter_kwh": "999"}
        )
        asyncio.run(daily.async_added_to_hass())
        self.assertIsNone(daily.native_value)
        self.assertIsNone(daily.extra_state_attributes["last_meter_kwh"])

    def test_meter_available_by_own_freshness_not_stale_pump(self):
        self.setup_platform()
        self.coordinator.ems_meters = {"METER_2": {"TOTAL_ACT_POW_FL_1": "1"}}
        self.coordinator.emit()
        entity = self.batches[-1][0]
        import time
        self.coordinator._meter_last_update["METER_2"] = time.time()
        self.assertTrue(entity.available)
        self.coordinator._meter_last_update["METER_2"] -= 120
        self.assertFalse(entity.available)
        self.coordinator._meter_last_update["METER_2"] = time.time()
        self.coordinator.ems_meters = {}
        self.assertFalse(entity.available)

    def test_pump_sensor_staleness_sets_ha_availability_not_string(self):
        import time
        self.coordinator.device = {"Data": {"TSM16": "23.5"}}
        self.coordinator._last_update = time.time()
        pump = self.sensor.EurosOSSensor(
            self.coordinator, "TSM16",
            ("Source temperature", "°C", "mdi:thermometer", "temperature"),
            "abcdef", {}, device_type="FriskoGEO",
        )
        self.assertTrue(pump.available)
        self.assertEqual(pump.native_value, 23.5)
        self.coordinator._last_update -= 61
        self.assertFalse(pump.available)
        # The last valid numeric reading is still in the snapshot;
        # Home Assistant writes unavailable because available is False.
        self.assertEqual(pump.native_value, 23.5)
        self.assertEqual(pump._attr_unique_id, "abcdef_tsm16")

    def test_missing_first_pump_snapshot_is_unavailable(self):
        pump = self.sensor.EurosOSSensor(
            self.coordinator, "TSM16",
            ("Source temperature", "°C", "mdi:thermometer", "temperature"),
            "abcdef", {}, device_type="FriskoGEO",
        )
        self.assertFalse(pump.available)
        self.assertIsNone(pump.native_value)

    def test_numeric_sensor_values_are_finite_for_ha_state_classes(self):
        cases = (("0", 0.0), ("16.75", 16.75), ("NaN", None),
                 ("inf", None), (None, None), ("not numeric", None), (True, None))
        for raw, expected in cases:
            with self.subTest(raw=raw):
                pump = self.sensor.EurosOSSensor(
                    self.coordinator, "SAMPLE",
                    ("Numeric", None, "mdi:gauge", None),
                    "abcdef", {}, device_type="FriskoATMO",
                )
                self.coordinator.device = {"Data": {"SAMPLE": raw}}
                self.assertEqual(pump.native_value, expected)
                self.assertEqual(pump._attr_state_class, "measurement")
                self.assertEqual(pump._attr_unique_id, "abcdef_sample")

    def test_incomplete_legacy_power_readings_are_unknown_not_zero(self):
        power = self.sensor.EurosOSSensor(
            self.coordinator, "ZM_AC_IN_PWR",
            ("Power", "W", "mdi:flash", "power"),
            "abcdef", {}, device_type="FriskoATMO",
        )
        for sample in ({"ZM_AC_IN_CUR": "2"}, {"ZM_AC_IN_VOL": "230"},
                       {"ZM_AC_IN_CUR": "NaN", "ZM_AC_IN_VOL": "230"}):
            with self.subTest(sample=sample):
                self.coordinator.device = {"Data": sample}
                self.assertIsNone(power.native_value)
        self.coordinator.device = {"Data": {
            "ZM_AC_IN_CUR": "2", "ZM_AC_IN_VOL": "230"
        }}
        self.assertEqual(power.native_value, 460.0)
        self.assertEqual(power._attr_native_unit_of_measurement, "W")
        self.assertEqual(power._attr_unique_id, "abcdef_zm_ac_in_pwr")

    def test_temperature_does_not_accept_nan_in_native_value(self):
        temperature = self.sensor.EurosOSSensor(
            self.coordinator, "TSM16",
            ("Temperature", "°C", "mdi:thermometer", "temperature"),
            "abcdef", {}, device_type="FriskoGEO",
        )
        self.coordinator.device = {"Data": {"TSM16": "NaN"}}
        self.assertIsNone(temperature.native_value)
        self.coordinator.device = {"Data": {"TSM16": 22.4}}
        self.assertEqual(temperature.native_value, 22.4)


    def _legacy_estimated_energy(self, restored=None):
        import time
        sensor = self.sensor.EurosOSLegacyEstimatedEnergySensor(
            self.coordinator, "ZM_AC_IN_ENERGY",
            ("Energy estimate", "kWh", "mdi:counter", "energy"),
            "abcdef", {}, device_type="FriskoATMO",
        )
        sensor.hass = types.SimpleNamespace(
            loop=types.SimpleNamespace(
                is_closed=lambda: False,
                call_soon_threadsafe=lambda fn: fn(),
            )
        )
        sensor._restored_sensor_data = restored
        self.coordinator._last_update = time.time()
        self.coordinator.device = {
            "Data": {"ZM_AC_IN_CUR": "2", "ZM_AC_IN_VOL": "230"}
        }
        asyncio.run(sensor.async_added_to_hass())
        return sensor

    def test_legacy_energy_is_stable_across_reads_and_meter_only_events(self):
        sensor = self._legacy_estimated_energy()
        baseline = self.coordinator._last_update
        self.assertEqual(sensor.native_value, 0.0)
        self.assertEqual(sensor._attr_unique_id, "abcdef_zm_ac_in_energy")
        self.assertEqual(sensor._attr_native_unit_of_measurement, "kWh")
        self.assertEqual(sensor._attr_device_class, "energy")
        self.assertEqual(sensor._attr_state_class, "total_increasing")
        for _ in range(5):
            self.assertEqual(sensor.native_value, 0.0)
            sensor._handle_coordinator_update()  # meter-only or staleness
        self.assertEqual(sensor.native_value, 0.0)
        self.coordinator._last_update = baseline + 30
        self.coordinator.device["Data"]["ZM_AC_IN_CUR"] = "4"
        sensor._handle_coordinator_update()
        # 460 -> 920 W trapezoid, 30 seconds = 0.00575 kWh.
        self.assertEqual(sensor.native_value, 0.0057)  # Python round(0.00575, 4)
        self.assertEqual(sensor.native_value, sensor.native_value)

    def test_legacy_energy_restores_native_value_without_offline_gap(self):
        restored = types.SimpleNamespace(native_value=12.3456)
        sensor = self._legacy_estimated_energy(restored=restored)
        first = self.coordinator._last_update
        self.assertEqual(sensor.native_value, 12.3456)
        self.coordinator._last_update = first + 30
        sensor._handle_coordinator_update()
        # 460 W for 30 seconds = 0.003833... kWh.
        self.assertEqual(sensor.native_value, round(12.3456 + 460 * 30 / 3_600_000, 4))
        self.assertEqual(sensor._attr_unique_id, "abcdef_zm_ac_in_energy")

    def test_legacy_energy_does_not_invent_power_during_outage(self):
        sensor = self._legacy_estimated_energy()
        first = self.coordinator._last_update
        self.coordinator._last_update = first + 240  # greater than MQTT_TIMEOUT
        sensor._handle_coordinator_update()
        self.assertEqual(sensor.native_value, 0.0)
        self.coordinator._last_update += 30
        sensor._handle_coordinator_update()
        self.assertEqual(sensor.native_value, round(460 * 30 / 3_600_000, 4))

    def test_legacy_energy_invalid_samples_break_integration_interval(self):
        sensor = self._legacy_estimated_energy()
        baseline = self.coordinator._last_update
        for timestamp, reading in (
            (baseline + 10, "NaN"), (baseline + 20, None),
            (baseline + 30, "-1"), (baseline + 40, "2"),
        ):
            self.coordinator._last_update = timestamp
            self.coordinator.device["Data"]["ZM_AC_IN_CUR"] = reading
            sensor._handle_coordinator_update()
        self.assertEqual(sensor.native_value, 0.0)
        self.coordinator._last_update += 10
        sensor._handle_coordinator_update()
        self.assertEqual(sensor.native_value, round(460 * 10 / 3_600_000, 4))
        asyncio.run(sensor.async_will_remove_from_hass())
        self.coordinator._last_update += 10
        sensor._handle_coordinator_update()
        self.assertEqual(sensor.native_value, round(460 * 10 / 3_600_000, 4))

    def test_legacy_energy_rejects_invalid_restored_values(self):
        for invalid in ("NaN", -4, "bad", float("inf")):
            with self.subTest(invalid=invalid):
                sensor = self._legacy_estimated_energy(
                    restored=types.SimpleNamespace(native_value=invalid)
                )
                self.assertEqual(sensor.native_value, 0.0)


if __name__ == "__main__":
    unittest.main()
