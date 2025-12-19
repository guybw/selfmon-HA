"""Binary sensor platform for SelfMon (Honeywell Galaxy Alarm) integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import mqtt
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_MODULE_PATH,
    CONF_SENSORS,
    CONF_SENSOR_NAME,
    CONF_SENSOR_ENABLED,
    CONF_SENSOR_TYPE,
    CONF_SENSOR_DEVICE_CLASS,
    CONF_SENSOR_ZONE_ID,
    DOMAIN,
    MANUFACTURER,
    PAYLOAD_OPEN,
    PAYLOAD_CLOSED,
    SENSOR_TYPE_ZONE_INPUT,
)

_LOGGER = logging.getLogger(__name__)

DEVICE_CLASS_MAP = {
    "door": BinarySensorDeviceClass.DOOR,
    "motion": BinarySensorDeviceClass.MOTION,
    "smoke": BinarySensorDeviceClass.SMOKE,
    "safety": BinarySensorDeviceClass.SAFETY,
    "window": BinarySensorDeviceClass.WINDOW,
    "garage_door": BinarySensorDeviceClass.GARAGE_DOOR,
    "vibration": BinarySensorDeviceClass.VIBRATION,
    "tamper": BinarySensorDeviceClass.TAMPER,
    "problem": BinarySensorDeviceClass.PROBLEM,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SelfMon binary sensors from a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    module_path = data[CONF_MODULE_PATH]
    sensors_config = data.get(CONF_SENSORS, {})

    entities = []

    for sensor_key, sensor_data in sensors_config.items():
        if not sensor_data.get(CONF_SENSOR_ENABLED, True):
            continue

        sensor_type = sensor_data.get(CONF_SENSOR_TYPE)

        if sensor_type == SENSOR_TYPE_ZONE_INPUT:
            entities.append(
                SelfMonZoneSensor(
                    module_path=module_path,
                    sensor_key=sensor_key,
                    sensor_config=sensor_data,
                    entry_id=config_entry.entry_id,
                )
            )

    async_add_entities(entities)


class SelfMonZoneSensor(BinarySensorEntity):
    """Representation of a SelfMon zone sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        module_path: str,
        sensor_key: str,
        sensor_config: dict[str, Any],
        entry_id: str,
    ) -> None:
        """Initialize the zone sensor."""
        self._module_path = module_path
        self._sensor_key = sensor_key
        self._sensor_config = sensor_config
        self._entry_id = entry_id

        self._zone_id = sensor_config.get(CONF_SENSOR_ZONE_ID, "")
        self._topic = sensor_config.get("topic", sensor_key)

        module_id = module_path.split(".")[-1] if "." in module_path else module_path
        self._attr_unique_id = f"selfmon_{module_id}_zone_{self._zone_id}"

        self._attr_name = sensor_config.get(CONF_SENSOR_NAME, f"Zone {self._zone_id}")

        device_class_str = sensor_config.get(CONF_SENSOR_DEVICE_CLASS, "None")
        if device_class_str and device_class_str != "None":
            self._attr_device_class = DEVICE_CLASS_MAP.get(device_class_str)

        self._attr_is_on = None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        module_id = self._module_path.split(".")[-1] if "." in self._module_path else self._module_path
        return DeviceInfo(
            identifiers={(DOMAIN, f"selfmon_{module_id}")},
            name="Honeywell Galaxy Alarm",
            manufacturer=MANUFACTURER,
            model=f"VMOD {module_id}",
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT topic when added to hass."""
        @callback
        def message_received(msg):
            """Handle new MQTT message."""
            payload = msg.payload
            if payload == PAYLOAD_OPEN:
                self._attr_is_on = True
            elif payload == PAYLOAD_CLOSED:
                self._attr_is_on = False
            else:
                _LOGGER.warning(
                    "Unexpected payload for %s: %s", self._topic, payload
                )
                return
            self.async_write_ha_state()

        self._unsubscribe = await mqtt.async_subscribe(
            self.hass, self._topic, message_received, qos=0
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from MQTT topic when removed."""
        if hasattr(self, "_unsubscribe"):
            self._unsubscribe()
