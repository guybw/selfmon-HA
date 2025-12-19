"""Constants for the SelfMon (Honeywell Galaxy Alarm) integration."""
from __future__ import annotations

DOMAIN = "selfmon"
MANUFACTURER = "SelfMon"

# Configuration keys
CONF_MODULE_PATH = "module_path"
CONF_SENSORS = "sensors"
CONF_SENSOR_NAME = "name"
CONF_SENSOR_ENABLED = "enabled"
CONF_SENSOR_TYPE = "sensor_type"
CONF_SENSOR_DEVICE_CLASS = "device_class"
CONF_SENSOR_ZONE_ID = "zone_id"
CONF_ENABLE_OUTPUTS = "enable_outputs"

# Sensor types
SENSOR_TYPE_ZONE_INPUT = "zone_input"
SENSOR_TYPE_OUTPUT = "output"
SENSOR_TYPE_TEMPERATURE = "temperature"
SENSOR_TYPE_VKP_LINE = "vkp_line"
SENSOR_TYPE_VERSION = "version"

# MQTT topic patterns
TOPIC_PRIO_INPUTS = "prio/inputs/read"
TOPIC_VRIO_INPUTS = "vrio/inputs/read"
TOPIC_PRIO_OUTPUTS = "prio/outputs"
TOPIC_VRIO_OUTPUTS = "vrio/outputs"
TOPIC_TEMPERATURE = "temperature"
TOPIC_VKP_LINE1 = "vkp/display/line1"
TOPIC_VKP_LINE2 = "vkp/display/line2"
TOPIC_VERSION = "version"

# Payloads
PAYLOAD_OPEN = "OPEN"
PAYLOAD_CLOSED = "CLOSED"
PAYLOAD_ON = "ON"
PAYLOAD_OFF = "OFF"

# Device classes for binary sensors
DEVICE_CLASS_OPTIONS = [
    "door",
    "motion",
    "smoke",
    "safety",
    "window",
    "garage_door",
    "vibration",
    "tamper",
    "problem",
    "None",
]

# Discovery timeout in seconds
DISCOVERY_TIMEOUT = 10
MODULE_DISCOVERY_TIMEOUT = 8
