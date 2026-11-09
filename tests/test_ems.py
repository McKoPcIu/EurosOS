"""Unit tests for the read-only EMS whole-home meter helpers."""

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "euros_os"
    / "ems.py"
)
spec = importlib.util.spec_from_file_location("euros_ems", MODULE_PATH)
ems = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ems)


class EmsMeterTests(unittest.TestCase):
    def test_all_33_home_meter_fields_and_two_daily_sensors(self):
        self.assertEqual(len(ems.EMS_DOM_SENSOR_DEFINITIONS), 33)
        self.assertEqual(len(ems.EMS_DOM_DAILY_SENSOR_DEFINITIONS), 2)
        self.assertEqual(len(ems.EMS_DOM_STAGE_1_DESCRIPTIONS), 15)
        self.assertEqual(ems.EMS_DOM_DEVICE_NAME, "EMS – Dom")
        self.assertEqual(ems.EMS_DOM_METER_NAME, "METER_1")

    def test_stage_1_sensor_names_types_units(self):
        fields = {
            "AB_LINE_VOLT_FL_1": ("Napięcie L1–L2", "V", "voltage"),
            "BC_LINE_VOLT_FL_1": ("Napięcie L2–L3", "V", "voltage"),
            "CA_LINE_VOLT_FL_1": ("Napięcie L3–L1", "V", "voltage"),
            "A_PHA_ACT_POW_FL_1": ("Moc czynna L1", "kW", "power"),
            "B_PHA_ACT_POW_FL_1": ("Moc czynna L2", "kW", "power"),
            "C_PHA_ACT_POW_FL_1": ("Moc czynna L3", "kW", "power"),
            "TOTAL_RACT_POW_FL_1": ("Moc bierna całkowita", "kvar", "reactive_power"),
            "A_PHA_VIEW_POW_FL_1": ("Moc pozorna L1", "kVA", "apparent_power"),
            "B_PHA_VIEW_POW_FL_1": ("Moc pozorna L2", "kVA", "apparent_power"),
            "C_PHA_VIEW_POW_FL_1": ("Moc pozorna L3", "kVA", "apparent_power"),
            "TOTAL_APPA_POWER_FL_1": ("Moc pozorna całkowita", "kVA", "apparent_power"),
            "A_PHA_POW_FAC_FL_1": ("Współczynnik mocy L1", None, "power_factor"),
            "B_PHA_POW_FAC_FL_1": ("Współczynnik mocy L2", None, "power_factor"),
            "C_PHA_POW_FAC_FL_1": ("Współczynnik mocy L3", None, "power_factor"),
            "TOTAL_POW_FAC_FL_1": ("Współczynnik mocy całkowity", None, "power_factor"),
        }
        self.assertEqual(len(fields), 15)
        self.assertEqual(set(ems.EMS_DOM_STAGE_1_DESCRIPTIONS), set(fields))
        for key, (label, unit, device_class) in fields.items():
            name, actual_unit, _, actual_class, state_class = (
                ems.EMS_DOM_SENSOR_DEFINITIONS[key]
            )
            self.assertEqual(name, "EMS – Dom – " + label)
            self.assertEqual(actual_unit, unit)
            self.assertEqual(actual_class, device_class)
            self.assertEqual(state_class, "measurement")
            self.assertGreater(len(ems.EMS_DOM_STAGE_1_DESCRIPTIONS[key]), 30)

    def test_meter_values_preserve_signed_phase_measurements(self):
        sample = {
            "A_PHA_ACT_POW_FL_1": "-0.015",
            "B_PHA_ACT_POW_FL_1": "0.073",
            "C_PHA_ACT_POW_FL_1": "0.008",
            "TOTAL_RACT_POW_FL_1": "-0.365",
            "TOTAL_POW_FAC_FL_1": "0.126",
            "AB_LINE_VOLT_FL_1": "407.9",
        }
        for key, raw in sample.items():
            self.assertIn(key, ems.EMS_DOM_SENSOR_DEFINITIONS)
            self.assertEqual(ems.parse_ems_numeric(raw), float(raw))

    def test_stage_2_all_eight_sensor_definitions(self):
        expected = {
            "POS_REAC_POW_FL_1": ("Energia bierna dodatnia", "kvarh", "reactive_energy", "total_increasing"),
            "REW_REAC_POW_FL_1": ("Energia bierna ujemna", "kvarh", "reactive_energy", "total_increasing"),
            "A_ACT_POW_FL_1": ("Moc L1 – odczyt techniczny", "kW", "power", "measurement"),
            "B_ACT_POW_FL_1": ("Moc L2 – odczyt techniczny", "kW", "power", "measurement"),
            "C_ACT_POW_FL_1": ("Moc L3 – odczyt techniczny", "kW", "power", "measurement"),
            "POS_ACT_POW_FACTOR": ("Współczynnik POS – techniczny", None, None, None),
            "REV_ACT_POW_FACTOR": ("Współczynnik REV – techniczny", None, None, None),
            "TOTAL_ACT_POW_FACTOR": ("Współczynnik TOTAL – techniczny", None, None, None),
        }
        self.assertEqual(len(expected), 8)
        self.assertEqual(set(ems.EMS_DOM_STAGE_2_DESCRIPTIONS), set(expected))
        for key, (label, unit, device_class, state_class) in expected.items():
            info = ems.EMS_DOM_SENSOR_DEFINITIONS[key]
            self.assertEqual(info[0], "EMS – Dom – " + label)
            self.assertEqual(info[1], unit)
            self.assertEqual(info[3], device_class)
            self.assertEqual(info[4], state_class)
            self.assertGreater(len(ems.EMS_DOM_STAGE_2_DESCRIPTIONS[key]), 50)

    def test_stage_2_diagnostic_keys_are_only_technical_fields(self):
        expected = {
            "A_ACT_POW_FL_1",
            "B_ACT_POW_FL_1",
            "C_ACT_POW_FL_1",
            "POS_ACT_POW_FACTOR",
            "REV_ACT_POW_FACTOR",
            "TOTAL_ACT_POW_FACTOR",
        }
        self.assertEqual(ems.EMS_DOM_STAGE_2_DIAGNOSTIC_KEYS, expected)
        self.assertNotIn("POS_REAC_POW_FL_1", expected)
        self.assertNotIn("REW_REAC_POW_FL_1", expected)
        self.assertTrue(expected.issubset(ems.EMS_DOM_SENSOR_DEFINITIONS))

    def test_stage_2_real_log_samples_keep_sign_and_precision(self):
        raw = {
            "POS_REAC_POW_FL_1": "165.92",
            "REW_REAC_POW_FL_1": "1321.49",
            "A_ACT_POW_FL_1": "-0.088",
            "B_ACT_POW_FL_1": "-0.148",
            "C_ACT_POW_FL_1": "-0.138",
            "POS_ACT_POW_FACTOR": "1",
            "REV_ACT_POW_FACTOR": "1",
            "TOTAL_ACT_POW_FACTOR": "-1",
        }
        for key, value in raw.items():
            self.assertEqual(ems.parse_ems_numeric(value), float(value))
        self.assertEqual(ems.parse_ems_numeric(None), None)
        self.assertEqual(ems.parse_ems_numeric("not a number"), None)

    def test_energy_counters_are_kwh_and_total_increasing(self):
        for key in ("POS_ACT_POW_FL_1", "REW_ACT_POW_FL_1"):
            self.assertEqual(ems.EMS_DOM_SENSOR_DEFINITIONS[key][1], "kWh")
            self.assertEqual(ems.EMS_DOM_SENSOR_DEFINITIONS[key][4], "total_increasing")

    def test_signed_grid_power_is_preserved(self):
        self.assertEqual(ems.parse_ems_numeric("2.01"), 2.01)
        self.assertEqual(ems.parse_ems_numeric("-0.125"), -0.125)
        self.assertEqual(ems.parse_ems_numeric("0"), 0.0)

    def test_missing_or_invalid_reading_is_not_a_false_zero(self):
        for value in (None, "", "unavailable", "NaN", "inf", "-inf", True, {}, []):
            self.assertIsNone(ems.parse_ems_numeric(value))

    def test_separates_geo_and_multiple_meter_devices(self):
        devices = [
            {"Name": "GEO_1", "Type": "FriskoGEO", "Data": {"TSM16": "24.2"}},
            {"Name": "METER_1", "Type": "METER", "Data": {
                "TOTAL_ACT_POW_FL_1": "0.168",
                "POS_ACT_POW_FL_1": "318.44",
                "REW_ACT_POW_FL_1": "10067.75",
            }},
            {"Name": "METER_2", "Type": "METER", "Data": {"TOTAL_ACT_POW_FL_1": "1"}},
        ]
        meters = ems.extract_ems_meters(devices)
        self.assertEqual(set(meters), {"METER_1", "METER_2"})
        self.assertEqual(ems.parse_ems_numeric(meters["METER_1"]["TOTAL_ACT_POW_FL_1"]), 0.168)
        self.assertNotIn("GEO_1", meters)

    def test_rejects_invalid_or_spoofed_meter(self):
        devices = [
            {"Name": "METER_1", "Type": "FriskoGEO", "Data": {"TOTAL_ACT_POW_FL_1": "999"}},
            {"Name": "WRONG", "Type": "METER", "Data": {"TOTAL_ACT_POW_FL_1": "999"}},
            {"Name": "METER_3", "Type": "METER", "Data": None},
            "bad",
        ]
        self.assertEqual(ems.extract_ems_meters(devices), {})
        self.assertEqual(ems.extract_ems_meters(None), {})

    def test_daily_counter_starts_from_physical_meter_baseline(self):
        day, total, last = ems.accumulate_ems_daily_energy(
            "2026-10-29", None, None, "2026-10-29", "319.28"
        )
        self.assertEqual((day, total, last), ("2026-10-29", 0.0, 319.28))
        day, total, last = ems.accumulate_ems_daily_energy(
            day, total, last, "2026-10-29", "319.37"
        )
        self.assertAlmostEqual(total, 0.09)
        day, total, last = ems.accumulate_ems_daily_energy(
            day, total, last, "2026-10-29", "319.37"
        )
        self.assertAlmostEqual(total, 0.09)

    def test_daily_counter_rollover_on_local_calendar_day(self):
        day, total, last = ems.accumulate_ems_daily_energy(
            "2026-10-29", 2.31, 321.59, "2026-10-30", 321.61
        )
        self.assertEqual((day, total, last), ("2026-10-30", 0.0, 321.61))
        day, total, last = ems.accumulate_ems_daily_energy(
            day, total, last, "2026-10-30", 321.66
        )
        self.assertAlmostEqual(total, 0.05)

    def test_midnight_timer_preserves_last_meter_counter(self):
        # A scheduled midnight reset sets today's total to zero, but leaves
        # the last lifetime reading so the first increment is not lost.
        day, total, last = ems.accumulate_ems_daily_energy(
            "2026-10-30", 0.0, 321.59, "2026-10-30", 321.61
        )
        self.assertEqual((day, total), ("2026-10-30", 0.02))
        self.assertEqual(last, 321.61)

    def test_daily_counter_restart_restores_accumulated_state(self):
        day, total, last = ems.accumulate_ems_daily_energy(
            "2026-10-29", 1.23, 319.28, "2026-10-29", 319.37
        )
        self.assertEqual(day, "2026-10-29")
        self.assertAlmostEqual(total, 1.32)
        self.assertEqual(last, 319.37)

    def test_daily_counter_ignores_bad_or_negative_measurements(self):
        prior = ("2026-10-29", 0.21, 10067.82)
        for invalid in (None, "unknown", float("nan"), "-1", True):
            self.assertEqual(
                ems.accumulate_ems_daily_energy(*prior, "2026-10-29", invalid),
                prior,
            )

    def test_daily_counter_ignores_small_fall_and_rebases_big_reset(self):
        prior = ("2026-10-29", 0.5, 10067.82)
        self.assertEqual(
            ems.accumulate_ems_daily_energy(*prior, "2026-10-29", 10067.81),
            prior,
        )
        day, total, last = ems.accumulate_ems_daily_energy(
            *prior, "2026-10-29", 0.0
        )
        self.assertEqual((day, total, last), ("2026-10-29", 0.5, 0.0))
        day, total, last = ems.accumulate_ems_daily_energy(
            day, total, last, "2026-10-29", 0.1
        )
        self.assertAlmostEqual(total, 0.6)

    def test_missing_meter_packet_clears_snapshot(self):
        self.assertEqual(
            ems.extract_ems_meters([{"Name": "GEO_1", "Type": "FriskoGEO", "Data": {}}]),
            {},
        )


if __name__ == "__main__":
    unittest.main()
