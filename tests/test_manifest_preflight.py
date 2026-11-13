"""Preflight guards for installing Euros OS as a custom integration in HA.

Catch duplicate JSON properties: the ordinary JSON parser silently keeps the
last property and previously hid the required paho-mqtt package.
"""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "custom_components" / "euros_os" / "manifest.json"


def reject_duplicate_keys(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"Duplicate manifest.json property: {key}")
        obj[key] = value
    return obj


class ManifestPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(
            MANIFEST.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_keys,
        )

    def test_manifest_declares_mqtt_dependency_once(self):
        requirements = self.manifest["requirements"]
        self.assertEqual(len(requirements), 1)
        self.assertTrue(requirements[0].startswith("paho-mqtt"))
        self.assertIn("<3", requirements[0])

    def test_manifest_core_fields(self):
        self.assertEqual(self.manifest["domain"], "euros_os")
        self.assertTrue(self.manifest["version"])
        self.assertTrue(self.manifest["config_flow"])
        self.assertTrue(self.manifest["documentation"].startswith("https://"))

    def test_push_telemetry_is_declared_consistently(self):
        hacs = json.loads(
            (ROOT / "hacs.json").read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_keys,
        )
        self.assertEqual(self.manifest["iot_class"], "local_push")
        self.assertEqual(hacs["iot_class"], self.manifest["iot_class"])
        self.assertEqual(hacs["domain"], self.manifest["domain"])
        self.assertEqual(hacs["filename"], "euros_os.zip")
        self.assertTrue(hacs["zip_release"])

    def test_expected_integration_files_present(self):
        for name in (
            "__init__.py", "coordinator.py", "config_flow.py",
            "discovery.py", "ems.py", "geo.py", "sensor.py",
            "switch.py", "select.py", "number.py", "binary_sensor.py",
        ):
            with self.subTest(file=name):
                self.assertTrue(
                    (ROOT / "custom_components" / "euros_os" / name).is_file(),
                    f"missing {name}",
                )


if __name__ == "__main__":
    unittest.main()
