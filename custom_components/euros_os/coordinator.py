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
from .const import MQTT_PORT, MQTT_USER, MQTT_PASSWORD

_LOGGER = logging.getLogger("custom_components.euros_os")

class EurosOSMQTTCoordinator(DataUpdateCoordinator):

    def __init__(self, ip, topic):
        super().__init__(None, _LOGGER, name="EurosOS")
        self.ip = ip
        self.topic = topic
        self.device = {}
        self.client = None
        self.connected = threading.Event()
        self._last_update = None
        self._listeners = []

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
                if "Devices" in payload:
                    self.device = payload["Devices"][0]
                    self._last_update = time.time()
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
