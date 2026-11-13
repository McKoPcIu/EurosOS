"""Regression checks for legacy and EMS energy-statistics metadata."""
import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "euros_os"


def read_literal_mapping(file, name):
    tree = ast.parse((ROOT / file).read_text(encoding="utf-8"))
    return ast.literal_eval(
        next(
            item.value for item in tree.body
            if isinstance(item, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == name
                    for target in item.targets)
        )
    )


class EnergyMetadataTests(unittest.TestCase):
    def test_known_sensor_units_and_classes_are_compatible(self):
        variables = read_literal_mapping("const.py", "SENSORS_VARIABLES")
        expected = {
            "ZM_AC_IN_VOL": ("V", "voltage"),
            "ZM_AC_IN_CUR": ("A", "current"),
            "ZM_AC_IN_PWR": ("W", "power"),
            "ZM_AC_IN_ENERGY": ("kWh", "energy"),
            "PWM_1": ("%", None),
            "ZM_FAN1_SPE": ("RPM", None),
            "ZM_FAN2_SPE": ("RPM", None),
        }
        for key, (unit, device_class) in expected.items():
            with self.subTest(key=key):
                self.assertEqual(variables[key][1], unit)
                self.assertEqual(variables[key][3], device_class)

    def test_ems_lifetime_and_daily_energy_classification(self):
        meter = read_literal_mapping("ems.py", "EMS_DOM_SENSOR_DEFINITIONS")
        daily = read_literal_mapping("ems.py", "EMS_DOM_DAILY_SENSOR_DEFINITIONS")
        for key in ("POS_ACT_POW_FL_1", "REW_ACT_POW_FL_1"):
            with self.subTest(key=key):
                self.assertEqual(meter[key][1], "kWh")
                self.assertEqual(meter[key][3:], ("energy", "total_increasing"))
                self.assertIn(key, daily)
        self.assertEqual(meter["TOTAL_ACT_POW_FL_1"][1:], (
            "kW", "mdi:transmission-tower", "power", "measurement"
        ))

    def test_legacy_estimated_energy_does_not_mutate_in_native_getter(self):
        tree = ast.parse((ROOT / "sensor.py").read_text(encoding="utf-8"))
        cls = next(node for node in tree.body
                   if isinstance(node, ast.ClassDef)
                   and node.name == "EurosOSLegacyEstimatedEnergySensor")
        self.assertIn("RestoreSensor", [
            node.id for node in cls.bases if isinstance(node, ast.Name)
        ])
        names = {node.name for node in cls.body
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertIn("_refresh_from_pump", names)
        self.assertIn("async_added_to_hass", names)
        self.assertNotIn("native_value", names)
        # Uses the base SensorEntity native_value getter without side effects.
        old = next(node for node in tree.body
                   if isinstance(node, ast.ClassDef)
                   and node.name == "EurosOSSensor")
        self.assertNotIn("_energy_kwh", ast.unparse(old))


if __name__ == "__main__":
    unittest.main()
