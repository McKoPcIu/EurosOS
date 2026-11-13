"""Unit tests for GEO-specific, dependency-free sensor helpers."""

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "euros_os"
    / "geo.py"
)
spec = importlib.util.spec_from_file_location("euros_geo", MODULE_PATH)
geo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geo)


class GeoSensorTests(unittest.TestCase):
    def test_p1_unverified_readings_excluded_for_geo_only(self):
        expected = {
            "ZM_AC_IN_VOL",
            "ZM_AC_IN_CUR",
            "ZM_AC_IN_PWR",
            "ZM_AC_IN_ENERGY",
            "ZM_SUCT_TEMP",
        }
        self.assertEqual(geo.GEO_P1_UNVERIFIED_SENSOR_KEYS, expected)
        # Exactly like the historic air-source fans: do not recreate the
        # GEO entities. Their registry IDs and recorded history are untouched.
        for key in expected:
            self.assertIn(key, geo.GEO_EXCLUDED_ENTITIES)
            self.assertFalse(geo.entity_supported_for_device(key, geo.GEO_DEVICE_TYPE))
            self.assertTrue(geo.entity_supported_for_device(key, "FriskoATMO"))
            self.assertTrue(geo.entity_supported_for_device(key, None))

    def test_geo_still_creates_operating_state_sensor(self):
        self.assertNotIn("STATE", geo.GEO_EXCLUDED_ENTITIES)
        self.assertTrue(geo.entity_supported_for_device("STATE", "FriskoGEO"))

    def test_p1_state_sensor_is_really_wired_to_safe_geo_helper(self):
        """Regression guard: testing geo.py alone did not update the HA sensor."""
        sensor_source = (
            MODULE_PATH.parent / "sensor.py"
        ).read_text(encoding="utf-8")
        self.assertIn("    calculate_geo_operating_state,", sensor_source)
        self.assertIn("if self.device_type == GEO_DEVICE_TYPE:", sensor_source)
        self.assertIn("return calculate_geo_operating_state(data)", sensor_source)
        self.assertIn("device_type=device_type", sensor_source)
        self.assertIn('self._attr_unique_id = f"{unique_prefix}_{key.lower()}"', sensor_source)
        self.assertIn('if self.key == "STATE":', sensor_source)

    def test_p1_geo_state_with_complete_realistic_log_flags_is_idle(self):
        sample = {
            "SBF_DHS": "1",
            "SBF_DHX": "1",
            "SBF_OOF": "1",
            "SBB_QHW": "0",
            "SXF_TOE": "1",
            "SBB_QHT": "0",
            "SBB_QHL": "0",
        }
        # All seven bits were present in the 357 sampled GEO_1 MQTT packets.
        self.assertEqual(geo.calculate_geo_operating_state(sample), "IDLE")

    def test_p1_geo_state_matches_old_cwu_and_co_conditions(self):
        sample = {
            "SBF_DHS": "1",
            "SBF_DHX": "1",
            "SBF_OOF": "1",
            "SBB_QHW": "0",
            "SXF_TOE": "1",
            "SBB_QHT": "0",
            "SBB_QHL": "0",
        }
        self.assertEqual(
            geo.calculate_geo_operating_state({**sample, "SBB_QHW": "1"}),
            "CWU",
        )
        self.assertEqual(
            geo.calculate_geo_operating_state({**sample, "SBB_QHT": "1"}),
            "CO",
        )
        self.assertEqual(
            geo.calculate_geo_operating_state({**sample, "SBB_QHL": "1"}),
            "CO",
        )
        # Preserve the existing CWU-first priority if both flags are active.
        self.assertEqual(
            geo.calculate_geo_operating_state(
                {**sample, "SBB_QHW": "1", "SBB_QHT": "1"}
            ),
            "CWU",
        )

    def test_p1_geo_state_off_is_not_idle(self):
        sample = {
            "SBF_DHS": "1",
            "SBF_DHX": "1",
            "SBF_OOF": "0",
            "SBB_QHW": "0",
            "SXF_TOE": "1",
            "SBB_QHT": "0",
            "SBB_QHL": "0",
        }
        self.assertEqual(geo.calculate_geo_operating_state(sample), "OFF")
        # An incomplete OFF packet must not be reported as OFF.
        del sample["SBB_QHW"]
        self.assertIsNone(geo.calculate_geo_operating_state(sample))

    def test_p1_geo_state_missing_flags_must_not_fake_idle(self):
        flags = {
            "SBF_DHS": "1",
            "SBF_DHX": "1",
            "SBF_OOF": "1",
            "SBB_QHW": "0",
            "SXF_TOE": "1",
            "SBB_QHT": "0",
            "SBB_QHL": "0",
        }
        for key in flags:
            partial = {k: v for k, v in flags.items() if k != key}
            self.assertIsNone(geo.calculate_geo_operating_state(partial))
        self.assertIsNone(geo.calculate_geo_operating_state({}))
        self.assertIsNone(geo.calculate_geo_operating_state(None))
        self.assertIsNone(geo.calculate_geo_operating_state("bad payload"))

    def test_p1_geo_state_rejects_invalid_flag_values(self):
        good = {
            "SBF_DHS": "1",
            "SBF_DHX": "1",
            "SBF_OOF": "1",
            "SBB_QHW": "0",
            "SXF_TOE": "1",
            "SBB_QHT": "0",
            "SBB_QHL": "0",
        }
        for invalid in (None, "", "unknown", "unavailable", "nan", "2", "-1", 1.5, True):
            self.assertIsNone(
                geo.calculate_geo_operating_state({**good, "SBF_OOF": invalid})
            )
        # Genuine 0 and 1 readings are allowed as Python ints as well.
        self.assertEqual(
            geo.calculate_geo_operating_state(
                {k: int(v) for k, v in good.items()}
            ),
            "IDLE",
        )

    def test_geo_device_firmware_version(self):
        self.assertEqual(
            geo.geo_device_software_version(
                {"Name": "GEO_1", "Version": "1_0", "Data": {"VER_S1": "870", "VER_S2": "12"}}
            ),
            "870.12",
        )
        self.assertIsNone(
            geo.geo_device_software_version(
                {"Version": "1_0", "Data": {"VER_S1": "870"}}
            )
        )
        self.assertIsNone(geo.geo_device_software_version({"Data": {"VER_S1": "", "VER_S2": "12"}}))
        self.assertIsNone(geo.geo_device_software_version({"Data": {"VER_S1": "bad", "VER_S2": "12"}}))
        self.assertIsNone(geo.geo_device_software_version({"Version": "1_0"}))
        self.assertIsNone(geo.geo_device_software_version(None))

    def test_geo_names_are_model_specific(self):
        original = ("Temp. powietrza zasysanego", "°C", "mdi:thermometer", "temperature")
        self.assertEqual(
            geo.sensor_info_for_device("T3fiz", original, "FriskoGEO")[0],
            "Dolne źródło — temperatura powrotu z gruntu",
        )
        self.assertEqual(geo.sensor_info_for_device("T3fiz", original, "Other"), original)
        self.assertEqual(geo.sensor_info_for_device("T3fiz", original, None), original)
        self.assertEqual(geo.sensor_info_for_device("OTHER", original, "FriskoGEO"), original)

    def test_air_source_entities_not_created_for_geo(self):
        excluded = ("ZM_FAN1_SPE", "ZM_FAN2_SPE", "ZM_DEFR_SIGN")
        for key in excluded:
            self.assertFalse(geo.entity_supported_for_device(key, "FriskoGEO"))
            self.assertTrue(geo.entity_supported_for_device(key, "Other"))
            self.assertTrue(geo.entity_supported_for_device(key, None))

    def test_heaters_and_other_geo_entities_remain(self):
        for key in ("SIO_R11", "SIO_R01", "TSM15", "TSM17", "T3fiz"):
            self.assertTrue(geo.entity_supported_for_device(key, "FriskoGEO"))

    def test_storage_tank_names_geo_only(self):
        originals = {
            "TSM15": ("Temp. zbiornika CWU", "°C", "mdi:thermometer", "temperature"),
            "TSM17": ("Temp. zbiornika buforowego", "°C", "mdi:thermometer", "temperature"),
        }
        expected = {
            "TSM15": "CWU — temperatura zbiornika",
            "TSM17": "CO — temperatura zbiornika",
        }
        for key, original in originals.items():
            self.assertEqual(
                geo.sensor_info_for_device(key, original, geo.GEO_DEVICE_TYPE)[0],
                expected[key],
            )
            self.assertEqual(
                geo.sensor_info_for_device(key, original, "Other"), original
            )

    def test_target_temperature_names_geo_only(self):
        originals = {
            "SX5": ("Temp. zadana CWU", "°C", "mdi:thermometer", "temperature"),
            "SX6": ("Temp. zadana CO", "°C", "mdi:thermometer", "temperature"),
        }
        expected = {
            "SX5": "CWU — temperatura zadana zbiornika",
            "SX6": "CO — temperatura zadana pomieszczenia",
        }
        for key, original in originals.items():
            self.assertEqual(
                geo.sensor_info_for_device(key, original, geo.GEO_DEVICE_TYPE)[0],
                expected[key],
            )
            self.assertEqual(
                geo.sensor_info_for_device(key, original, "Other"), original
            )

    def test_ambient_temperature_labels_geo_only(self):
        labels = {
            "TSM10": "Temperatura wewnętrzna - aktualna",
            "TSM9": "Temperatura zewnętrzna - aktualna",
            "TOUT_KOR": "Temperatura zewnętrzna - średnia z pompy",
            "TSM16": "Temp. wejściowa czynnika (sprężarka)",
        }
        for key, name in labels.items():
            original = ("Old temperature label", "°C", "mdi:thermometer", "temperature")
            self.assertEqual(
                geo.sensor_info_for_device(key, original, "FriskoGEO"),
                (name, *original[1:]),
            )
            self.assertEqual(
                geo.sensor_info_for_device(key, original, "AnotherType"),
                original,
            )

    def test_ground_source_labels_sort_together(self):
        original = ("Original", "°C", "mdi:thermometer", "temperature")
        names = [
            geo.sensor_info_for_device(key, original, geo.GEO_DEVICE_TYPE)[0]
            for key in ("T3fiz", "T4fiz")
        ]
        names.append(geo.GEO_GROUND_SOURCE_DELTA_T_NAME)
        self.assertEqual(
            sorted(names),
            [
                "Dolne źródło — temperatura powrotu z gruntu",
                "Dolne źródło — temperatura różnicowa (ΔT)",
                "Dolne źródło — temperatura wyjścia do gruntu",
            ],
        )

    def test_upper_source_labels_sort_together(self):
        original = ("Original", "°C", "mdi:thermometer", "temperature")
        labels = [
            geo.sensor_info_for_device(key, original, geo.GEO_DEVICE_TYPE)[0]
            for key in ("T5fiz", "TSM13")
        ]
        labels.append(geo.GEO_UPPER_SOURCE_DELTA_T_NAME)
        self.assertEqual(
            sorted(labels),
            [
                "Górne źródło — temperatura powrotu",
                "Górne źródło — temperatura różnicowa (ΔT)",
                "Górne źródło — temperatura zasilania",
            ],
        )
        self.assertEqual(
            geo.sensor_info_for_device("T5fiz", original, "Other"), original
        )

    def test_upper_source_delta(self):
        self.assertEqual(
            geo.calculate_upper_source_delta_t({"TSM13": 27.4, "T5fiz": 22.3}),
            5.1,
        )
        self.assertEqual(
            geo.calculate_upper_source_delta_t({"TSM13": 19.1, "T5fiz": 20.2}),
            -1.1,
        )
        self.assertIsNone(geo.calculate_upper_source_delta_t({"TSM13": 27.4}))
        self.assertIsNone(
            geo.calculate_upper_source_delta_t({"TSM13": "nan", "T5fiz": 22.3})
        )

    def test_delta_positive_and_negative(self):
        self.assertEqual(geo.calculate_ground_source_delta_t({"T3fiz": "10.9", "T4fiz": "8.8"}), 2.1)
        self.assertEqual(geo.calculate_ground_source_delta_t({"T3fiz": "2", "T4fiz": "4"}), -2.0)

    def test_delta_missing_invalid_or_out_of_range(self):
        self.assertIsNone(geo.calculate_ground_source_delta_t({"T3fiz": "10"}))
        self.assertIsNone(geo.calculate_ground_source_delta_t({"T3fiz": "bad", "T4fiz": "8"}))
        self.assertIsNone(geo.calculate_ground_source_delta_t({"T3fiz": "nan", "T4fiz": "8"}))
        self.assertIsNone(geo.calculate_ground_source_delta_t({"T3fiz": "150", "T4fiz": "8"}))


if __name__ == "__main__":
    unittest.main()
