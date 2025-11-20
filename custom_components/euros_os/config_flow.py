"""
===============================================================================
Euros OS Home Assistant Custom Integration
===============================================================================

File        : config_flow.py
Author      : Patryk "KoPcIu" Kopeć / https://github.com/McKoPcIu/EurosOS
Integration : euros_os
Version     : 0.1.0
Description : Custom integration for EurosEnergy and E-On devices.

===============================================================================
"""

import asyncio
import json
import logging
import ssl
import threading
import ipaddress
import platform
import subprocess
import voluptuous as vol
import paho.mqtt.client as mqtt

from homeassistant import config_entries
from .const import DOMAIN, CONF_KEY, DEFAULT_KEY, CONF_IP, DEFAULT_IP, MQTT_USER, MQTT_PASSWORD, MQTT_PORT

_LOGGER = logging.getLogger("custom_components.euros_os")

class EurosOSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        schema = vol.Schema({
            vol.Required(CONF_KEY, default=DEFAULT_KEY): str,
            vol.Required(CONF_IP, default=DEFAULT_IP): str
        })

        if user_input is not None:
            key = user_input[CONF_KEY]
            ip = user_input[CONF_IP]
            topic = f"{key}/Dev"

            if not is_valid_host(ip):
                errors["base"] = "invalid_ip"
                return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

            for entry in self._async_current_entries():
                if entry.data.get(CONF_KEY) == key:
                    errors["base"] = "already_configured"
                    return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

            try:
                _LOGGER.debug("Checking MQTT topic availability: %s on %s", topic, ip)
                device_data = await self.hass.async_add_executor_job(
                    self._verify_mqtt_topic, ip, topic
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
                return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
            except Exception as e:
                _LOGGER.exception("Error during MQTT validation: %s", e)
                errors["base"] = "unknown"
                return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

            return self.async_create_entry(
                title=f"Euros OS ({key})",
                data={
                    CONF_KEY: key,
                    CONF_IP: ip,
                    "device_model": device_data["device_model"],
                    "device_type": device_data["device_type"],
                    "device_version": device_data["device_version"]
                }
            )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    def _verify_mqtt_topic(self, ip: str, topic: str):
        event = threading.Event()
        payload_container = {}

        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                _LOGGER.debug("Connected to MQTT broker at %s:%s", ip, MQTT_PORT)
                client.subscribe(topic)
            else:
                _LOGGER.error("Failed to connect to MQTT broker, rc=%s", rc)
                client.disconnect()

        def on_message(client, userdata, msg):
            try:
                payload = json.loads(msg.payload)
                if "Devices" in payload:
                    payload_container["data"] = payload
                    event.set()
                    client.disconnect()
            except Exception:
                _LOGGER.warning("Received invalid JSON on %s", topic)

        client = mqtt.Client()
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
        client.on_connect = on_connect
        client.on_message = on_message
        client.tls_set_context(ssl._create_unverified_context())

        try:
            client.connect(ip, MQTT_PORT, 60)
        except Exception as e:
            _LOGGER.error("Cannot connect to MQTT broker: %s", e)
            raise CannotConnect

        client.loop_start()
        if not event.wait(timeout=3.0):
            client.loop_stop()
            raise CannotConnect("No response from the device via MQTT.")
        client.loop_stop()

        if not payload_container:
            raise CannotConnect("No response from the device via MQTT.")

        _LOGGER.debug("Received valid MQTT message: %s", payload_container["data"])
        device_info = payload_container["data"].get("Devices", [{}])[0]
        device_model = device_info.get("Name", "---")
        device_type = device_info.get("Type", "---")
        device_version = device_info.get("Version", "---")

        return {"device_model": device_model, "device_type": device_type, "device_version": device_version}


class CannotConnect(Exception):
    """Failed to connect to the device."""
    pass


def is_valid_host(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False