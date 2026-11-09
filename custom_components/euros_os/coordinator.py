"""
===============================================================================
Euros OS Home Assistant Custom Integration
===============================================================================

File        : coordinator.py
Author      : Patryk "KoPcIu" Kopeć / https://github.com/McKoPcIu/EurosOS
Integration : euros_os
Version     : 0.1.0
Description : Custom integration for EurosEnergy and E-On devices.

===============================================================================
"""

import threading
import time
import json
import logging
import math
import re
import ssl
import paho.mqtt.client as mqtt
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import callback
from .const import MQTT_PORT, MQTT_USER, MQTT_PASSWORD
from .ems import extract_ems_meters, parse_ems_numeric

_LOGGER = logging.getLogger("custom_components.euros_os")

# Temporary, read-only EMS diagnostics. Only documented numeric meter fields
# are logged; credentials, identifiers and raw GEO payloads are never included.
_EMS_METER_FIELDS = frozenset({
    "A_PHA_VOLT_FL_1",
    "B_PHA_VOLT_FL_1",
    "C_PHA_VOLT_FL_1",
    "AB_LINE_VOLT_FL_1",
    "BC_LINE_VOLT_FL_1",
    "CA_LINE_VOLT_FL_1",
    "A_PHA_CUR_FL_1",
    "B_PHA_CUR_FL_1",
    "C_PHA_CUR_FL_1",
    "A_PHA_ACT_POW_FL_1",
    "B_PHA_ACT_POW_FL_1",
    "C_PHA_ACT_POW_FL_1",
    "TOTAL_ACT_POW_FL_1",
    "A_ACT_POW_FL_1",
    "B_ACT_POW_FL_1",
    "C_ACT_POW_FL_1",
    "TOTAL_RACT_POW_FL_1",
    "A_PHA_VIEW_POW_FL_1",
    "B_PHA_VIEW_POW_FL_1",
    "C_PHA_VIEW_POW_FL_1",
    "TOTAL_APPA_POWER_FL_1",
    "A_PHA_POW_FAC_FL_1",
    "B_PHA_POW_FAC_FL_1",
    "C_PHA_POW_FAC_FL_1",
    "TOTAL_POW_FAC_FL_1",
    "FREQUENCY_FL_1",
    "POS_ACT_POW_FL_1",
    "REW_ACT_POW_FL_1",
    "POS_REAC_POW_FL_1",
    "REW_REAC_POW_FL_1",
    "POS_ACT_POW_FACTOR",
    "REV_ACT_POW_FACTOR",
    "TOTAL_ACT_POW_FACTOR",
})
_EMS_METER_LOG_INTERVAL = 30.0  # seconds
_EMS_NO_METER_LOG_INTERVAL = 300.0  # seconds

class EurosOSMQTTCoordinator(DataUpdateCoordinator):

    def __init__(self, ip, topic):
        super().__init__(None, _LOGGER, name="EurosOS")
        self.ip = ip
        self.topic = topic
        self.device = {}
        self.ems_meters = {}  # Current read-only METER_N data, separate from GEO.
        self.client = None
        self.connected = threading.Event()
        self._last_update = None
        self._listeners = []
        self._last_ems_diagnostic = None
        self._last_ems_meter_present = None
        self._last_ems_power_received = None

    # ------------------ Listeners ------------------
    def async_add_listener(self, callback):
        if callback not in self._listeners:
            self._listeners.append(callback)

    def async_remove_listener(self, callback):
        if callback in self._listeners:
            self._listeners.remove(callback)

    @callback
    def _notify_listeners(self):
        for callback in self._listeners:
            callback()

    # ------------------ Read-only EMS diagnostics ------------------
    def _log_ems_diagnostics(self, devices):
        """Summarize the complete MQTT Devices list without disclosing secrets.

        Does not alter the current device, subscribe to other topics, or publish.
        Logs only numeric values with known electrical meter parameter names.
        """
        if not isinstance(devices, list):
            return

        meters = []
        geo_count = 0
        other_count = 0
        for device in devices:
            if not isinstance(device, dict):
                other_count += 1
                continue
            name = device.get("Name")
            device_type = device.get("Type")
            meter_name = (
                isinstance(name, str)
                and re.fullmatch(r"METER_[0-9]{1,2}", name, re.IGNORECASE)
            )
            meter_type = (
                isinstance(device_type, str)
                and device_type.upper() == "METER"
            )
            if meter_name or meter_type:
                # Never print a device identifier other than a validated METER_N.
                safe_name = name.upper() if meter_name else "METER_UNNAMED"
                data = device.get("Data")
                data = data if isinstance(data, dict) else {}
                values = {}
                for key in sorted(_EMS_METER_FIELDS & data.keys()):
                    value = data[key]
                    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
                        continue
                    if isinstance(value, str) and len(value) > 32:
                        continue
                    try:
                        if math.isfinite(float(value)):
                            values[key] = value  # Raw value, no assumptions about scaling.
                    except (ValueError, TypeError, OverflowError):
                        continue
                meters.append((safe_name, values, len(data)))
            elif isinstance(name, str) and name.upper().startswith("GEO_"):
                geo_count += 1
            else:
                other_count += 1

        now = time.monotonic()
        has_meter = bool(meters)
        interval = _EMS_METER_LOG_INTERVAL if has_meter else _EMS_NO_METER_LOG_INTERVAL
        if (
            self._last_ems_diagnostic is not None
            and self._last_ems_meter_present == has_meter
            and now - self._last_ems_diagnostic < interval
        ):
            return
        self._last_ems_diagnostic = now
        self._last_ems_meter_present = has_meter

        _LOGGER.info(
            "[EMS_DIAG] MQTT /Dev: Devices=%d, GEO=%d, METER=%d, OTHER=%d",
            len(devices), geo_count, len(meters), other_count,
        )
        for safe_name, values, total_keys in meters:
            _LOGGER.info(
                "[EMS_DIAG] %s: numeric_fields=%d, all_data_fields=%d, values=%s",
                safe_name, len(values), total_keys,
                json.dumps(values, sort_keys=True, ensure_ascii=True, separators=(",", ":")),
            )

    def _log_ems_power_sample(self, meters, received_at, received_monotonic):
        """Log each valid METER_1 power sample only when DEBUG is enabled.

        Times represent MQTT reception, not the physical meter sampling time.
        Never log the complete payload, credentials, or device identifiers.
        """
        if not _LOGGER.isEnabledFor(logging.DEBUG):
            return
        reading = meters.get("METER_1")
        if not isinstance(reading, dict):
            return
        power_kw = parse_ems_numeric(reading.get("TOTAL_ACT_POW_FL_1"))
        if power_kw is None:
            return
        elapsed = (
            None if self._last_ems_power_received is None
            else round(received_monotonic - self._last_ems_power_received, 3)
        )
        self._last_ems_power_received = received_monotonic
        _LOGGER.debug(
            "[EMS_POWER_SAMPLE] received_unix=%.3f power_kw=%.6f "
            "power_w=%.3f delta_receive_s=%s",
            received_at, power_kw, power_kw * 1000,
            elapsed if elapsed is not None else "first",
        )

    # ------------------ MQTT ------------------
    def connect(self):
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                _LOGGER.debug("Connected to MQTT broker at %s", self.ip)
                client.subscribe(self.topic)
                self.connected.set()
            else:
                _LOGGER.error("Failed to connect to MQTT broker, rc=%s", rc)

        def on_message(client, userdata, msg):
            try:
                payload = json.loads(msg.payload)
                devices = payload.get("Devices")
                if isinstance(devices, list) and devices:
                    self._log_ems_diagnostics(devices)
                    received_at = time.time()
                    received_monotonic = time.monotonic()
                    meters = extract_ems_meters(devices)
                    self._log_ems_power_sample(meters, received_at, received_monotonic)
                    self.ems_meters = meters
                    self.device = devices[0]
                    self._last_update = received_at
                    _LOGGER.debug("Received MQTT payload: %s", self.device)
                    self._notify_listeners()
            except Exception as e:
                _LOGGER.warning("Invalid JSON on %s: %s", self.topic, e)

        client = mqtt.Client()
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
        client.on_connect = on_connect
        client.on_message = on_message
        client.tls_set_context(ssl._create_unverified_context())

        try:
            client.connect(self.ip, MQTT_PORT, 60)
        except Exception as e:
            _LOGGER.error("Cannot connect to MQTT broker: %s", e)
            return

        self.client = client
        client.loop_start()
        if not self.connected.wait(timeout=5.0):
            _LOGGER.error("Timeout waiting for MQTT connection to %s", self.ip)

    # ------------------ DataSending ------------------
    async def async_set_device_value(self, data: dict, entry_data: dict = None):
        if not self.client:
            _LOGGER.warning("MQTT client not connected")
            return False

        device_name = entry_data.get("device_model") if entry_data else None
        device_type = entry_data.get("device_type") if entry_data else None
        device_version = entry_data.get("device_version") if entry_data else None

        if not all([device_name, device_type, device_version]):
            _LOGGER.error(
                "Cannot publish: missing device info - "
                f"device_name={device_name}, device_type={device_type}, device_version={device_version}"
            )
            return False

        payload = json.dumps({
            "Devices": [
                {
                    "Name": device_name,
                    "Data": data,
                    "Type": device_type,
                    "Version": device_version
                }
            ]
        })

        topic = self.topic.replace("/Dev", "") + "/App"
        _LOGGER.debug("Publishing to %s: %s", topic, payload)
        self.client.publish(topic, payload, retain=False)
        return True

    # ------------------ DataUpdateCoordinator ------------------
    async def _async_update_data(self):
        return self.device
