"""Stage 9: security and lifecycle wiring checks, no HA or broker required."""
from pathlib import Path
import ast
import unittest


BASE = Path(__file__).resolve().parents[1] / "custom_components" / "euros_os"


def read(name):
    source = (BASE / name).read_text(encoding="utf-8")
    ast.parse(source, filename=name)
    return source


class Stage9ReliabilityTests(unittest.TestCase):
    def test_watchdog_registers_on_ha_loop_and_is_removed_on_unload(self):
        source = read("__init__.py")
        self.assertIn("from homeassistant.helpers.event import async_track_time_interval", source)
        self.assertIn("coordinator.check_stale()", source)
        self.assertIn("async_track_time_interval(", source)
        self.assertIn("watchdog_unsub()", source)
        self.assertIn('["watchdog_unsub"]', source)

    def test_coordinator_notifies_once_after_mqtt_timeout(self):
        source = read("coordinator.py")
        self.assertIn("def check_stale(self, now=None):", source)
        self.assertIn("current - self._last_update > MQTT_TIMEOUT", source)
        self.assertIn("current - timestamp > MQTT_TIMEOUT", source)
        self.assertIn("self._reported_stale_meters = stale_meters", source)
        self.assertIn("if newly_stale:", source)
        self.assertIn("self._notify_listeners()", source)

    def test_pump_sensor_uses_ha_availability_instead_of_literal_state(self):
        source = read("sensor.py")
        start = source.index("class EurosOSSensor(")
        end = source.index("class EurosOSEMSMeterSensor(", start)
        pump_class = source[start:end]
        self.assertIn("def available(self):", pump_class)
        self.assertNotIn('return "unavailable"', pump_class)

    def test_no_device_key_or_raw_payload_in_debug_command_logs(self):
        coordinator = read("coordinator.py")
        flow = read("config_flow.py")
        self.assertNotIn('"Publishing to %s: %s"', coordinator)
        self.assertNotIn('"Received valid MQTT message: %s"', flow)
        self.assertNotIn('"Checking MQTT topic availability: %s on %s"', flow)
        self.assertNotIn('"Invalid JSON on %s: %s"', coordinator)

    def test_all_pump_controls_expose_freshness_as_availability(self):
        for name in ("number.py", "select.py", "switch.py", "binary_sensor.py"):
            with self.subTest(name=name):
                source = read(name)
                self.assertIn("def available(self):", source)
                self.assertIn("self.coordinator.pump_is_fresh()", source)
        coordinator = read("coordinator.py")
        self.assertIn("def pump_is_fresh(self, now=None):", coordinator)
        self.assertIn("if not self.pump_is_fresh():", coordinator)

    def test_diagnostic_samples_are_not_logged_at_info_level(self):
        coordinator = read("coordinator.py")
        start = coordinator.index("    def _log_ems_diagnostics(")
        end = coordinator.index("    # ------------------ MQTT ------------------", start)
        diagnostic = coordinator[start:end]
        self.assertIn("logging.DEBUG", diagnostic)
        self.assertNotIn("_LOGGER.info(", diagnostic)
        self.assertNotIn("json.dumps", diagnostic)
        self.assertNotIn("values=%s", diagnostic)


if __name__ == "__main__":
    unittest.main()
