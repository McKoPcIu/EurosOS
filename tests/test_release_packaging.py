"""Offline smoke tests for a Marketplace-compatible euros_os.zip release."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_release_zip.py"


class ReleasePackagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("euros_os_zip_builder", BUILD)
        cls.builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.builder)

    def test_release_archive_has_flat_integration_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "euros_os.zip"
            members = self.builder.build_archive(output)
            self.assertTrue(output.exists())
            self.assertIn("__init__.py", members)
            self.assertIn("manifest.json", members)
            self.assertIn("sensor.py", members)
            self.assertIn("geo.py", members)
            self.assertIn("ems.py", members)
            self.assertIn("translations/en.json", members)
            self.assertNotIn("custom_components/euros_os/manifest.json", members)
            self.assertFalse(any("__pycache__" in n or n.endswith(".pyc") for n in members))
            with zipfile.ZipFile(output) as archive:
                self.assertIsNone(archive.testzip())
                manifest = json.loads(archive.read("manifest.json"))
                self.assertEqual(manifest["domain"], "euros_os")
                self.assertTrue(manifest["version"])
                for member in members:
                    self.assertEqual(
                        archive.read(member),
                        (ROOT / "custom_components" / "euros_os" / member).read_bytes(),
                    )

    def test_release_metadata_links_to_upstream_package_name(self):
        hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
        self.assertTrue(hacs["zip_release"])
        self.assertEqual(hacs["filename"], "euros_os.zip")
        self.assertEqual(hacs["domain"], "euros_os")
        self.assertEqual(hacs["iot_class"], "local_push")

    def test_archive_contains_no_private_runtime_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            members = self.builder.build_archive(Path(tmp) / "euros_os.zip")
        forbidden = (".storage", "secrets.yaml", "home-assistant_v2.db", "config_entries",
                     ".env", "euros_os_pre_etap", ".tar.gz")
        for name in members:
            with self.subTest(name=name):
                self.assertFalse(any(item in name for item in forbidden))
                self.assertFalse(name.startswith("/"))
                self.assertNotIn("..", Path(name).parts)


if __name__ == "__main__":
    unittest.main()
