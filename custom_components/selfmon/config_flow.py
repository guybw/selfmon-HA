"""Config flow for SelfMon (Honeywell Galaxy Alarm) integration."""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_ENABLE_OUTPUTS,
    CONF_MODULE_PATH,
    CONF_SENSORS,
    CONF_SENSOR_NAME,
    CONF_SENSOR_ENABLED,
    CONF_SENSOR_TYPE,
    CONF_SENSOR_DEVICE_CLASS,
    CONF_SENSOR_ZONE_ID,
    DEVICE_CLASS_OPTIONS,
    DISCOVERY_TIMEOUT,
    DOMAIN,
    MODULE_DISCOVERY_TIMEOUT,
    SENSOR_TYPE_ZONE_INPUT,
    SENSOR_TYPE_OUTPUT,
    SENSOR_TYPE_TEMPERATURE,
    SENSOR_TYPE_VKP_LINE,
    SENSOR_TYPE_VERSION,
    TOPIC_PRIO_INPUTS,
    TOPIC_VRIO_INPUTS,
    TOPIC_PRIO_OUTPUTS,
    TOPIC_VRIO_OUTPUTS,
    TOPIC_TEMPERATURE,
    TOPIC_VKP_LINE1,
    TOPIC_VKP_LINE2,
    TOPIC_VERSION,
)

_LOGGER = logging.getLogger(__name__)


def get_default_device_class(zone_id: str, topic: str) -> str:
    """Guess a default device class based on zone ID patterns."""
    zone_num = int(zone_id) if zone_id.isdigit() else 0
    last_digit = zone_num % 10
    if last_digit in (1, 7):
        return "door"
    elif last_digit in (2, 8):
        return "motion"
    elif last_digit in (4, 6):
        return "smoke"
    elif last_digit in (3, 5):
        return "safety"
    return "None"


def get_default_sensor_name(sensor_type: str, sensor_id: str) -> str:
    """Generate a default sensor name."""
    if sensor_type == SENSOR_TYPE_ZONE_INPUT:
        return f"Alarm - Zone {sensor_id}"
    elif sensor_type == SENSOR_TYPE_OUTPUT:
        return f"Alarm - Output {sensor_id}"
    elif sensor_type == SENSOR_TYPE_TEMPERATURE:
        return "Temperature Sensor"
    elif sensor_type == SENSOR_TYPE_VKP_LINE:
        if "line1" in sensor_id.lower():
            return "Keypad Line 1"
        return "Keypad Line 2"
    elif sensor_type == SENSOR_TYPE_VERSION:
        return "Module Version"
    return f"Sensor {sensor_id}"


class SelfMonConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SelfMon (Honeywell Galaxy Alarm)."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._module_path: str = ""
        self._discovered_modules: set[str] = set()
        self._discovered_sensors: dict[str, dict[str, Any]] = {}
        self._current_sensor_index: int = 0
        self._sensor_keys: list[str] = []
        self._enable_outputs: bool = False

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - auto-discover modules."""
        if not await mqtt.async_wait_for_mqtt_client(self.hass):
            return self.async_abort(reason="mqtt_not_available")

        self._discovered_modules = set()

        @callback
        def module_discovered(msg):
            """Handle discovered module topics."""
            topic = msg.topic
            match = re.match(r"(selfmon/vmod\.[a-fA-F0-9]+)", topic)
            if match:
                self._discovered_modules.add(match.group(1))
                _LOGGER.debug("Discovered module: %s from topic: %s", match.group(1), topic)

        # Subscribe to multiple patterns to increase chance of discovery
        # Some topics may have retained messages
        subscribe_patterns = [
            "selfmon/vmod.+/temperature",
            "selfmon/vmod.+/version", 
            "selfmon/vmod.+/heartbeat",
            "selfmon/vmod.+/vkp/display/#",
            "selfmon/vmod.+/prio/#",
            "selfmon/vmod.+/vrio/#",
            "selfmon/#",
        ]
        
        unsubscribes = []
        for pattern in subscribe_patterns:
            try:
                unsub = await mqtt.async_subscribe(
                    self.hass, pattern, module_discovered, qos=0
                )
                unsubscribes.append(unsub)
            except Exception as ex:
                _LOGGER.debug("Failed to subscribe to %s: %s", pattern, ex)

        await asyncio.sleep(MODULE_DISCOVERY_TIMEOUT)
        
        for unsub in unsubscribes:
            unsub()

        _LOGGER.debug("Discovery complete. Found modules: %s", self._discovered_modules)

        if not self._discovered_modules:
            return self.async_show_form(
                step_id="manual_entry",
                data_schema=vol.Schema({
                    vol.Required(CONF_MODULE_PATH, default="selfmon/vmod.010aa1"): str,
                }),
                errors={"base": "no_modules_found"},
            )

        if len(self._discovered_modules) == 1:
            self._module_path = list(self._discovered_modules)[0]
            await self.async_set_unique_id(self._module_path)
            self._abort_if_unique_id_configured()
            return await self.async_step_output_config()

        return await self.async_step_select_module()

    async def async_step_select_module(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let user select from discovered modules."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._module_path = user_input[CONF_MODULE_PATH]
            await self.async_set_unique_id(self._module_path)
            self._abort_if_unique_id_configured()
            return await self.async_step_output_config()

        module_options = sorted(list(self._discovered_modules))

        return self.async_show_form(
            step_id="select_module",
            data_schema=vol.Schema({
                vol.Required(CONF_MODULE_PATH): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=module_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }),
            errors=errors,
        )

    async def async_step_manual_entry(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual module path entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            module_path = user_input[CONF_MODULE_PATH].strip().rstrip("/")

            if not re.match(r"^selfmon/vmod\.[a-fA-F0-9]+$", module_path):
                errors["base"] = "invalid_path"
            else:
                await self.async_set_unique_id(module_path)
                self._abort_if_unique_id_configured()

                self._module_path = module_path
                return await self.async_step_output_config()

        return self.async_show_form(
            step_id="manual_entry",
            data_schema=vol.Schema({
                vol.Required(CONF_MODULE_PATH, default="selfmon/vmod.010aa1"): str,
            }),
            errors=errors,
        )

    async def async_step_output_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask user if they want to configure outputs."""
        if user_input is not None:
            self._enable_outputs = user_input.get(CONF_ENABLE_OUTPUTS, False)
            return await self.async_step_discover()

        return self.async_show_form(
            step_id="output_config",
            data_schema=vol.Schema({
                vol.Required(CONF_ENABLE_OUTPUTS, default=False): bool,
            }),
            description_placeholders={
                "module_path": self._module_path,
            },
        )

    async def async_step_discover(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Discover sensors from MQTT."""
        self._discovered_sensors = {}
        
        topics_to_subscribe = [
            f"{self._module_path}/{TOPIC_PRIO_INPUTS}/#",
            f"{self._module_path}/{TOPIC_VRIO_INPUTS}/#",
            f"{self._module_path}/{TOPIC_TEMPERATURE}",
            f"{self._module_path}/{TOPIC_VKP_LINE1}",
            f"{self._module_path}/{TOPIC_VKP_LINE2}",
            f"{self._module_path}/{TOPIC_VERSION}",
        ]

        if self._enable_outputs:
            topics_to_subscribe.extend([
                f"{self._module_path}/{TOPIC_PRIO_OUTPUTS}/#",
                f"{self._module_path}/{TOPIC_VRIO_OUTPUTS}/#",
            ])

        unsubscribes = []

        @callback
        def message_received(msg):
            """Handle received MQTT message for discovery."""
            topic = msg.topic
            _LOGGER.debug("Discovered topic: %s", topic)

            relative_topic = topic.replace(f"{self._module_path}/", "", 1)
            sensor_key = topic

            if relative_topic.startswith(TOPIC_PRIO_INPUTS) or relative_topic.startswith(TOPIC_VRIO_INPUTS):
                zone_id = relative_topic.split("/")[-1]
                sensor_type = SENSOR_TYPE_ZONE_INPUT
                device_class = get_default_device_class(zone_id, topic)
                self._discovered_sensors[sensor_key] = {
                    CONF_SENSOR_TYPE: sensor_type,
                    CONF_SENSOR_ZONE_ID: zone_id,
                    CONF_SENSOR_NAME: get_default_sensor_name(sensor_type, zone_id),
                    CONF_SENSOR_DEVICE_CLASS: device_class,
                    CONF_SENSOR_ENABLED: True,
                    "topic": topic,
                    "is_prio": TOPIC_PRIO_INPUTS in relative_topic,
                    "auto_enabled": False,
                }
            elif relative_topic.startswith(TOPIC_PRIO_OUTPUTS) or relative_topic.startswith(TOPIC_VRIO_OUTPUTS):
                output_id = relative_topic.split("/")[-1]
                sensor_type = SENSOR_TYPE_OUTPUT
                self._discovered_sensors[sensor_key] = {
                    CONF_SENSOR_TYPE: sensor_type,
                    CONF_SENSOR_ZONE_ID: output_id,
                    CONF_SENSOR_NAME: get_default_sensor_name(sensor_type, output_id),
                    CONF_SENSOR_DEVICE_CLASS: "None",
                    CONF_SENSOR_ENABLED: True,
                    "topic": topic,
                    "is_prio": TOPIC_PRIO_OUTPUTS in relative_topic,
                    "auto_enabled": False,
                }
            elif relative_topic == TOPIC_TEMPERATURE:
                self._discovered_sensors[sensor_key] = {
                    CONF_SENSOR_TYPE: SENSOR_TYPE_TEMPERATURE,
                    CONF_SENSOR_ZONE_ID: "temperature",
                    CONF_SENSOR_NAME: get_default_sensor_name(SENSOR_TYPE_TEMPERATURE, ""),
                    CONF_SENSOR_DEVICE_CLASS: "temperature",
                    CONF_SENSOR_ENABLED: True,
                    "topic": topic,
                    "auto_enabled": True,
                }
            elif relative_topic in (TOPIC_VKP_LINE1, TOPIC_VKP_LINE2):
                line_id = "line1" if "line1" in relative_topic else "line2"
                self._discovered_sensors[sensor_key] = {
                    CONF_SENSOR_TYPE: SENSOR_TYPE_VKP_LINE,
                    CONF_SENSOR_ZONE_ID: line_id,
                    CONF_SENSOR_NAME: get_default_sensor_name(SENSOR_TYPE_VKP_LINE, line_id),
                    CONF_SENSOR_DEVICE_CLASS: "None",
                    CONF_SENSOR_ENABLED: True,
                    "topic": topic,
                    "auto_enabled": True,
                }
            elif relative_topic == TOPIC_VERSION:
                self._discovered_sensors[sensor_key] = {
                    CONF_SENSOR_TYPE: SENSOR_TYPE_VERSION,
                    CONF_SENSOR_ZONE_ID: "version",
                    CONF_SENSOR_NAME: get_default_sensor_name(SENSOR_TYPE_VERSION, ""),
                    CONF_SENSOR_DEVICE_CLASS: "None",
                    CONF_SENSOR_ENABLED: True,
                    "topic": topic,
                    "auto_enabled": True,
                }

        for topic_pattern in topics_to_subscribe:
            try:
                unsub = await mqtt.async_subscribe(
                    self.hass, topic_pattern, message_received, qos=0
                )
                unsubscribes.append(unsub)
            except Exception as ex:
                _LOGGER.error("Failed to subscribe to %s: %s", topic_pattern, ex)

        await asyncio.sleep(DISCOVERY_TIMEOUT)

        for unsub in unsubscribes:
            unsub()

        if not self._discovered_sensors:
            return self.async_show_form(
                step_id="manual_entry",
                data_schema=vol.Schema({
                    vol.Required(CONF_MODULE_PATH, default=self._module_path): str,
                }),
                errors={"base": "no_sensors_found"},
            )

        self._sensor_keys = [
            key for key, data in sorted(self._discovered_sensors.items())
            if not data.get("auto_enabled", False)
        ]
        self._current_sensor_index = 0

        if not self._sensor_keys:
            return self.async_create_entry(
                title="Honeywell Galaxy Alarm",
                data={
                    CONF_MODULE_PATH: self._module_path,
                    CONF_SENSORS: self._discovered_sensors,
                    CONF_ENABLE_OUTPUTS: self._enable_outputs,
                },
            )

        return await self.async_step_sensor_config()

    async def async_step_sensor_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure individual sensors one by one."""
        if user_input is not None:
            current_key = self._sensor_keys[self._current_sensor_index]
            self._discovered_sensors[current_key][CONF_SENSOR_ENABLED] = user_input.get(CONF_SENSOR_ENABLED, True)
            self._discovered_sensors[current_key][CONF_SENSOR_NAME] = user_input.get(CONF_SENSOR_NAME, "")
            if CONF_SENSOR_DEVICE_CLASS in user_input:
                self._discovered_sensors[current_key][CONF_SENSOR_DEVICE_CLASS] = user_input[CONF_SENSOR_DEVICE_CLASS]

            self._current_sensor_index += 1

            if self._current_sensor_index >= len(self._sensor_keys):
                return self.async_create_entry(
                    title="Honeywell Galaxy Alarm",
                    data={
                        CONF_MODULE_PATH: self._module_path,
                        CONF_SENSORS: self._discovered_sensors,
                        CONF_ENABLE_OUTPUTS: self._enable_outputs,
                    },
                )

        if self._current_sensor_index >= len(self._sensor_keys):
            return self.async_create_entry(
                title="Honeywell Galaxy Alarm",
                data={
                    CONF_MODULE_PATH: self._module_path,
                    CONF_SENSORS: self._discovered_sensors,
                    CONF_ENABLE_OUTPUTS: self._enable_outputs,
                },
            )

        current_key = self._sensor_keys[self._current_sensor_index]
        sensor_data = self._discovered_sensors[current_key]
        sensor_type = sensor_data[CONF_SENSOR_TYPE]
        zone_id = sensor_data[CONF_SENSOR_ZONE_ID]

        description_text = f"Sensor {self._current_sensor_index + 1} of {len(self._sensor_keys)}\n"
        description_text += f"Topic: {sensor_data['topic']}\n"
        description_text += f"Type: {sensor_type}"

        schema_dict = {
            vol.Required(CONF_SENSOR_ENABLED, default=sensor_data.get(CONF_SENSOR_ENABLED, True)): bool,
            vol.Required(CONF_SENSOR_NAME, default=sensor_data.get(CONF_SENSOR_NAME, "")): str,
        }

        if sensor_type == SENSOR_TYPE_ZONE_INPUT:
            schema_dict[vol.Required(
                CONF_SENSOR_DEVICE_CLASS,
                default=sensor_data.get(CONF_SENSOR_DEVICE_CLASS, "None")
            )] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=DEVICE_CLASS_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )

        return self.async_show_form(
            step_id="sensor_config",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "sensor_id": f"{sensor_type} - {zone_id}",
                "sensor_num": str(self._current_sensor_index + 1),
                "total_sensors": str(len(self._sensor_keys)),
                "topic": sensor_data["topic"],
            },
            last_step=(self._current_sensor_index == len(self._sensor_keys) - 1),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return SelfMonOptionsFlow(config_entry)


class SelfMonOptionsFlow(config_entries.OptionsFlow):
    """Handle SelfMon options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry
        self._sensors = dict(config_entry.data.get(CONF_SENSORS, {}))
        self._sensor_keys: list[str] = []
        self._current_sensor_index: int = 0

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            self._sensor_keys = [
                key for key, data in sorted(self._sensors.items())
                if not data.get("auto_enabled", False)
            ]
            self._current_sensor_index = 0
            if self._sensor_keys:
                return await self.async_step_sensor_config()
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional("reconfigure", default=True): bool,
            }),
        )

    async def async_step_sensor_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure individual sensors."""
        if user_input is not None:
            current_key = self._sensor_keys[self._current_sensor_index]
            self._sensors[current_key][CONF_SENSOR_ENABLED] = user_input.get(CONF_SENSOR_ENABLED, True)
            self._sensors[current_key][CONF_SENSOR_NAME] = user_input.get(CONF_SENSOR_NAME, "")
            if CONF_SENSOR_DEVICE_CLASS in user_input:
                self._sensors[current_key][CONF_SENSOR_DEVICE_CLASS] = user_input[CONF_SENSOR_DEVICE_CLASS]

            self._current_sensor_index += 1

            if self._current_sensor_index >= len(self._sensor_keys):
                new_data = dict(self._config_entry.data)
                new_data[CONF_SENSORS] = self._sensors
                self.hass.config_entries.async_update_entry(
                    self._config_entry, data=new_data
                )
                return self.async_create_entry(title="", data={})

        current_key = self._sensor_keys[self._current_sensor_index]
        sensor_data = self._sensors[current_key]
        sensor_type = sensor_data[CONF_SENSOR_TYPE]

        schema_dict = {
            vol.Required(CONF_SENSOR_ENABLED, default=sensor_data.get(CONF_SENSOR_ENABLED, True)): bool,
            vol.Required(CONF_SENSOR_NAME, default=sensor_data.get(CONF_SENSOR_NAME, "")): str,
        }

        if sensor_type == SENSOR_TYPE_ZONE_INPUT:
            schema_dict[vol.Required(
                CONF_SENSOR_DEVICE_CLASS,
                default=sensor_data.get(CONF_SENSOR_DEVICE_CLASS, "None")
            )] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=DEVICE_CLASS_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )

        return self.async_show_form(
            step_id="sensor_config",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "sensor_id": f"{sensor_type} - {sensor_data[CONF_SENSOR_ZONE_ID]}",
            },
            last_step=(self._current_sensor_index == len(self._sensor_keys) - 1),
        )
