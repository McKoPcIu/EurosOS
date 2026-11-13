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
import ssl
import paho.mqtt.client as mqtt
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import callback
from .const import MQTT_PORT, MQTT_USER, MQTT_PASSWORD, MQTT_TIMEOUT
from .ems import extract_ems_meters
from .discovery import find_pump

_LOGGER = logging.getLogger("custom_components.euros_os")

_EMS_NO_METER_LOG_INTERVAL = 300.0  # seconds, only when DEBUG is enabled

class EurosOSMQTTCoordinator(DataUpdateCoordinator):

    def __init__(self, ip, topic, pump_name=None, pump_type=None, event_loop=None):
        super().__init__(None, _LOGGER, name="EurosOS")
        self.ip = ip
        self.topic = topic
        self.pump_name = pump_name
        self.pump_type = pump_type
        self._event_loop = event_loop
        self._closed = False
        self.device = {}
        self.ems_meters = {}  # Current read-only METER_N data, separate from GEO.
        self._meter_last_update = {}  # Independent receive time for each meter.
        self.client = None
        self.connected = threading.Event()
        self._last_update = None
        self._listeners = []
        self._last_ems_diagnostic = None
        self._reported_stale_pump = False
        self._reported_stale_meters = frozenset()

    # ------------------ Listeners ------------------
    def async_add_listener(self, callback):
        if callback not in self._listeners:
            self._listeners.append(callback)

    def async_remove_listener(self, callback):
        if callback in self._listeners:
            self._listeners.remove(callback)

    @callback
    def _notify_listeners(self):
        # MQTT callbacks run in a worker thread; HA entity callbacks must run
        # on the Home Assistant event loop, not directly in that worker.
        if self._closed:
            return
        if self._event_loop is not None:
            if self._event_loop.is_closed():
                return
            try:
                self._event_loop.call_soon_threadsafe(self._dispatch_listeners)
            except RuntimeError:
                # HA may close its event loop between is_closed() and queueing.
                _LOGGER.debug("Skipping MQTT update: Home Assistant loop is closed")
        else:
            self._dispatch_listeners()

    @callback
    def _dispatch_listeners(self):
        if self._closed:
            return
        for listener in tuple(self._listeners):
            listener()

    def pump_is_fresh(self, now=None):
        """Whether the configured pump has reported recently enough for controls."""
        if self._closed or self._last_update is None:
            return False
        current = time.time() if now is None else now
        return current - self._last_update <= MQTT_TIMEOUT

    @callback
    def check_stale(self, now=None):
        """Notify HA once when an already-received MQTT snapshot expires.

        A silent broker sends no message, so the scheduled HA watchdog must
        explicitly write unavailable states. Do not erase snapshots, create
        entities, publish commands, or refresh timestamps.
        """
        if self._closed:
            return False
        current = time.time() if now is None else now
        stale_pump = (
            self._last_update is not None
            and current - self._last_update > MQTT_TIMEOUT
        )
        stale_meters = frozenset(
            name for name, timestamp in self._meter_last_update.items()
            if current - timestamp > MQTT_TIMEOUT
        )
        newly_stale = (
            (stale_pump and not self._reported_stale_pump)
            or bool(stale_meters - self._reported_stale_meters)
        )
        self._reported_stale_pump = stale_pump
        self._reported_stale_meters = stale_meters
        if newly_stale:
            self._notify_listeners()
        return newly_stale

    # ------------------ Read-only EMS diagnostics ------------------
    def _log_ems_diagnostics(self, devices):
        """Low-volume debug counters, without device names or measurements."""
        if not _LOGGER.isEnabledFor(logging.DEBUG) or not isinstance(devices, list):
            return
        now = time.monotonic()
        if (
            self._last_ems_diagnostic is not None
            and now - self._last_ems_diagnostic < _EMS_NO_METER_LOG_INTERVAL
        ):
            return
        self._last_ems_diagnostic = now
        meter_count = sum(
            isinstance(item, dict)
            and isinstance(item.get("Type"), str)
            and item["Type"].upper() == "METER"
            for item in devices
        )
        _LOGGER.debug(
            "[EMS_DIAG] device_count=%d meter_count=%d",
            len(devices), meter_count,
        )

    # ------------------ MQTT ------------------
    def disconnect(self):
        """Stop the MQTT worker when the HA config entry is unloaded.

        Do not delete device snapshots or HA entity registry entries.
        """
        self._closed = True
        client = self.client
        self.client = None
        self.connected.clear()
        if client is None:
            return
        try:
            client.disconnect()
        except Exception as exc:
            # A broker/socket failure must not block unloading the HA entry.
            _LOGGER.warning("MQTT disconnect failed (%s)", type(exc).__name__)
        finally:
            try:
                client.loop_stop()
            except Exception as exc:
                _LOGGER.warning("MQTT worker shutdown failed (%s)", type(exc).__name__)

    def connect(self):
        self._closed = False
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                _LOGGER.debug("Connected to Euros OS MQTT broker")
                client.subscribe(self.topic)
                self.connected.set()
            else:
                _LOGGER.error("Failed to connect to MQTT broker, rc=%s", rc)

        def on_disconnect(client, userdata, rc, *args):
            self.connected.clear()
            if not self._closed and rc != 0:
                _LOGGER.warning("MQTT connection lost (rc=%s); retaining last valid readings", rc)

        def on_message(client, userdata, msg):
            if self._closed:
                return
            try:
                payload = json.loads(msg.payload)
                if not isinstance(payload, dict):
                    return
                devices = payload.get("Devices")
                if not isinstance(devices, list) or not devices:
                    return

                self._log_ems_diagnostics(devices)
                received_at = time.time()
                pump = find_pump(
                    devices, expected_name=self.pump_name, expected_type=self.pump_type
                )
                meters = extract_ems_meters(devices)

                if pump is None:
                    # Only accept packets made entirely of METER devices.
                    # Another/ambiguous/unknown pump must never masquerade
                    # as a meter-only update to this configured entry.
                    meter_only = all(
                        isinstance(device, dict)
                        and isinstance(device.get("Type"), str)
                        and device["Type"].upper() == "METER"
                        for device in devices
                    )
                    if not meter_only or not meters:
                        _LOGGER.debug("Ignoring MQTT packet without configured pump or usable meters")
                        return

                    # A meter-only update must not refresh pump freshness.
                    # Replace mapping snapshots atomically: HA may iterate
                    # the old mappings on its event loop simultaneously.
                    self.ems_meters = {**self.ems_meters, **meters}
                    self._meter_last_update = {
                        **self._meter_last_update,
                        **{name: received_at for name in meters},
                    }
                else:
                    # Pump-containing /Dev payload is a complete snapshot.
                    # Missing meters become unavailable but registered HA
                    # entities and their history are never deleted.
                    self.device = pump
                    self._last_update = received_at
                    self.ems_meters = meters
                    self._meter_last_update = {
                        name: received_at for name in meters
                    }
                    _LOGGER.debug("Received MQTT pump telemetry")

                self._notify_listeners()
            except Exception as e:
                _LOGGER.debug("Ignoring malformed MQTT telemetry (%s)", type(e).__name__)

        client = mqtt.Client()
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message
        client.tls_set_context(ssl._create_unverified_context())

        self.client = client
        try:
            client.connect(self.ip, MQTT_PORT, 60)
            client.loop_start()
            if not self.connected.wait(timeout=5.0):
                raise ConnectionError("MQTT connection acknowledgement timed out")
        except Exception as exc:
            # A failed setup must not leave a running Paho worker. HA can
            # retry the config entry when the broker is reachable again.
            self.disconnect()
            raise ConnectionError("Euros OS MQTT connection unavailable") from exc

    # ------------------ DataSending ------------------
    async def async_set_device_value(self, data: dict, entry_data: dict = None):
        if not self.client or not self.connected.is_set():
            _LOGGER.warning("MQTT command rejected: connection is unavailable")
            return False
        if not self.pump_is_fresh():
            _LOGGER.warning("MQTT command rejected: pump telemetry is stale")
            return False

        device_name = entry_data.get("device_model") if entry_data else None
        device_type = entry_data.get("device_type") if entry_data else None
        device_version = entry_data.get("device_version") if entry_data else None

        if not all([device_name, device_type, device_version]):
            _LOGGER.error("Cannot publish: incomplete device information")
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
        _LOGGER.debug("Publishing Euros OS device command")
        try:
            published = self.client.publish(topic, payload, retain=False)
        except Exception as exc:
            _LOGGER.warning("MQTT command publish failed (%s)", type(exc).__name__)
            return False
        if getattr(published, "rc", None) != mqtt.MQTT_ERR_SUCCESS:
            _LOGGER.warning("MQTT command was not accepted by the client")
            return False
        # Accepted for sending is not confirmation that the pump applied it.
        return True

    # ------------------ DataUpdateCoordinator ------------------
    async def _async_update_data(self):
        return self.device
