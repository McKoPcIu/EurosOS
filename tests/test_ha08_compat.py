"""Dependency-free guards for Home Assistant entity/device API migrations (HA-08)."""

import ast
from pathlib import Path
import unittest


INTEGRATION = Path(__file__).resolve().parents[1] / "custom_components" / "euros_os"


def source_tree(name: str) -> tuple[str, ast.Module]:
    source = (INTEGRATION / name).read_text(encoding="utf-8")
    return source, ast.parse(source, filename=name)


class Ha08CompatibilityTests(unittest.TestCase):
    def test_number_entity_does_not_override_legacy_unit_property(self):
        source, tree = source_tree("number.py")
        number = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "EurosOSNumber"
        )
        self.assertNotIn(
            "unit_of_measurement",
            {node.name for node in number.body if isinstance(node, ast.FunctionDef)},
        )
        self.assertIn("self._attr_native_unit_of_measurement = info[1]", source)
        self.assertIn("self._attr_unique_id = f", source)
        self.assertIn("async def async_set_native_value(self, value):", source)

    def test_legacy_pump_sensor_uses_current_native_ha_api_without_id_change(self):
        source, tree = source_tree("sensor.py")
        legacy = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "EurosOSSensor"
        )
        names = {
            node.name for node in legacy.body if isinstance(node, ast.FunctionDef)
        }
        self.assertIn("native_value", names)
        self.assertIn("available", names)
        self.assertNotIn("state", names)
        self.assertNotIn("unit_of_measurement", names)
        self.assertNotIn("state_class", names)
        self.assertIn("self._attr_native_unit_of_measurement = info[1]", source)
        self.assertIn("self._attr_state_class = (", source)
        self.assertIn('self._attr_unique_id = f"{unique_prefix}_{key.lower()}"', source)

    def test_geo_ems_device_links_to_existing_parent_by_registry_id(self):
        source, tree = source_tree("sensor.py")
        self.assertIsInstance(tree, ast.Module)
        self.assertIn("parent_device = dr.async_get(hass).async_get_or_create(", source)
        self.assertIn("config_entry_id=entry.entry_id", source)
        self.assertIn('"via_device_id": parent_device.id', source)
        self.assertNotIn('"via_device":', source)
        self.assertLess(
            source.index("parent_device = dr.async_get(hass).async_get_or_create("),
            source.index('"via_device_id": parent_device.id'),
        )
        self.assertIn('f"{unique_prefix}_ems_{meter_name.lower()}_{key.lower()}"', source)

    def test_changes_are_only_metadata_not_mqtt_control(self):
        source, _ = source_tree("number.py")
        self.assertIn("await self.coordinator.async_set_device_value(payload, entry_data)", source)
        self.assertIn("mode = self._get_device_mode()", source)


if __name__ == "__main__":
    unittest.main()
