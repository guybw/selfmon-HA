"""Sensor platform for SelfMon (Honeywell Galaxy Alarm) integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import mqtt
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_MODULE_PATH,
    CONF_SENSORS,
    CONF_SENSOR_NAME,
    CONF_SENSOR_ENABLED,
    CONF_SENSOR_TYPE,
    CONF_SENSOR_ZONE_ID,
    DOMAIN,
    MANUFACTURER,
    PAYLOAD_ON,
    PAYLOAD_OFF,
    SENSOR_TYPE_OUTPUT,
    SENSOR_TYPE_TEMPERATURE,
    SENSOR_TYPE_VKP_LINE,
    SENSOR_TYPE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SelfMon sensors from a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    module_path = data[CONF_MODULE_PATH]
    sensors_config = data.get(CONF_SENSORS, {})

    entities = []

    for sensor_key, sensor_data in sensors_config.items():
        if not sensor_data.get(CONF_SENSOR_ENABLED, True):
            continue

        sensor_type = sensor_data.get(CONF_SENSOR_TYPE)

        if sensor_type == SENSOR_TYPE_OUTPUT:
            entities.append(
                SelfMonOutputSensor(
                    module_path=module_path,
                    sensor_key=sensor_key,
                    sensor_config=sensor_data,
                    entry_id=config_entry.entry_id,
                )
            )
        elif sensor_type == SENSOR_TYPE_TEMPERATURE:
            entities.append(
                SelfMonTemperatureSensor(
                    module_path=module_path,
                    sensor_key=sensor_key,
                    sensor_config=sensor_data,
                    entry_id=config_entry.entry_id,
                )
            )
        elif sensor_type == SENSOR_TYPE_VKP_LINE:
            entities.append(
                SelfMonVKPSensor(
                    module_path=module_path,
                    sensor_key=sensor_key,
                    sensor_config=sensor_data,
                    entry_id=config_entry.entry_id,
                )
            )
        elif sensor_type == SENSOR_TYPE_VERSION:
            entities.append(
                SelfMonVersionSensor(
                    module_path=module_path,
                    sensor_key=sensor_key,
                    sensor_config=sensor_data,
                    entry_id=config_entry.entry_id,
                )
            )

    async_add_entities(entities)


class SelfMonBaseSensor(SensorEntity):
    """Base class for SelfMon sensors."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        module_path: str,
        sensor_key: str,
        sensor_config: dict[str, Any],
        entry_id: str,
    ) -> None:
        """Initialize the sensor."""
        self._module_path = module_path
        self._sensor_key = sensor_key
        self._sensor_config = sensor_config
        self._entry_id = entry_id

        self._zone_id = sensor_config.get(CONF_SENSOR_ZONE_ID, "")
        self._topic = sensor_config.get("topic", sensor_key)

        self._attr_native_value = None

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

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from MQTT topic when removed."""
        if hasattr(self, "_unsubscribe"):
            self._unsubscribe()


class SelfMonOutputSensor(SelfMonBaseSensor):
    """Representation of a SelfMon output sensor."""

    def __init__(
        self,
        module_path: str,
        sensor_key: str,
        sensor_config: dict[str, Any],
        entry_id: str,
    ) -> None:
        """Initialize the output sensor."""
        super().__init__(module_path, sensor_key, sensor_config, entry_id)

        module_id = module_path.split(".")[-1] if "." in module_path else module_path
        self._attr_unique_id = f"selfmon_{module_id}_output_{self._zone_id}"
        self._attr_name = sensor_config.get(CONF_SENSOR_NAME, f"Output {self._zone_id}")

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT topic when added to hass."""
        @callback
        def message_received(msg):
            """Handle new MQTT message."""
            payload = msg.payload
            if payload in (PAYLOAD_ON, PAYLOAD_OFF):
                self._attr_native_value = payload
            else:
                self._attr_native_value = payload
            self.async_write_ha_state()

        self._unsubscribe = await mqtt.async_subscribe(
            self.hass, self._topic, message_received, qos=0
        )


class SelfMonTemperatureSensor(SelfMonBaseSensor):
    """Representation of a SelfMon temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        module_path: str,
        sensor_key: str,
        sensor_config: dict[str, Any],
        entry_id: str,
    ) -> None:
        """Initialize the temperature sensor."""
        super().__init__(module_path, sensor_key, sensor_config, entry_id)

        module_id = module_path.split(".")[-1] if "." in module_path else module_path
        self._attr_unique_id = f"selfmon_{module_id}_temperature"
        self._attr_name = sensor_config.get(CONF_SENSOR_NAME, "Temperature")

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT topic when added to hass."""
        @callback
        def message_received(msg):
            """Handle new MQTT message."""
            try:
                self._attr_native_value = float(msg.payload)
                self.async_write_ha_state()
            except ValueError:
                _LOGGER.warning(
                    "Invalid temperature value: %s", msg.payload
                )

        self._unsubscribe = await mqtt.async_subscribe(
            self.hass, self._topic, message_received, qos=0
        )


class SelfMonVKPSensor(SelfMonBaseSensor):
    """Representation of a SelfMon virtual keypad display sensor."""

    def __init__(
        self,
        module_path: str,
        sensor_key: str,
        sensor_config: dict[str, Any],
        entry_id: str,
    ) -> None:
        """Initialize the VKP sensor."""
        super().__init__(module_path, sensor_key, sensor_config, entry_id)

        module_id = module_path.split(".")[-1] if "." in module_path else module_path
        line_id = self._zone_id
        self._attr_unique_id = f"selfmon_{module_id}_vkp_{line_id}"
        self._attr_name = sensor_config.get(CONF_SENSOR_NAME, f"Keypad {line_id.title()}")

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT topic when added to hass."""
        @callback
        def message_received(msg):
            """Handle new MQTT message."""
            self._attr_native_value = msg.payload
            self.async_write_ha_state()

        self._unsubscribe = await mqtt.async_subscribe(
            self.hass, self._topic, message_received, qos=0
        )


class SelfMonVersionSensor(SelfMonBaseSensor):
    """Representation of a SelfMon version sensor."""

    def __init__(
        self,
        module_path: str,
        sensor_key: str,
        sensor_config: dict[str, Any],
        entry_id: str,
    ) -> None:
        """Initialize the version sensor."""
        super().__init__(module_path, sensor_key, sensor_config, entry_id)

        module_id = module_path.split(".")[-1] if "." in module_path else module_path
        self._attr_unique_id = f"selfmon_{module_id}_version"
        self._attr_name = sensor_config.get(CONF_SENSOR_NAME, "Version")
        self._attr_icon = "mdi:information-outline"

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT topic when added to hass."""
        @callback
        def message_received(msg):
            """Handle new MQTT message."""
            self._attr_native_value = msg.payload
            self.async_write_ha_state()

        self._unsubscribe = await mqtt.async_subscribe(
            self.hass, self._topic, message_received, qos=0
        )
