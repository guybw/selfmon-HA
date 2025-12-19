# SelfMon - Honeywell Galaxy Alarm Integration for Home Assistant

A custom Home Assistant integration for Honeywell Galaxy alarm systems using the SelfMon Virtual Module (VMOD) via MQTT.

## Features

- **Auto-discovery**: Automatically discovers your VMOD module on the MQTT broker
- **Configurable sensors**: Name and configure each zone sensor during setup
- **Output toggle**: Choose whether to include output sensors
- **Device classes**: Assign appropriate device classes (door, motion, smoke, safety, etc.)
- **Always-on sensors**: Temperature and keypad display sensors are automatically enabled
- **Full entity support**:
  - Binary sensors for zone inputs (doors, motion, smoke, safety)
  - Sensors for outputs (siren, intruder, fire, set status) - optional
  - Temperature sensor (always enabled)
  - Virtual keypad display lines 1 & 2 (always enabled)
  - Module version sensor (always enabled)

## Prerequisites

1. **SelfMon Virtual Module (VMOD)** installed and connected to your Galaxy alarm panel
2. **MQTT broker** (e.g., Mosquitto) configured and running
3. **MQTT integration** configured in Home Assistant
4. VMOD configured to publish to your MQTT broker

## Installation

### Manual Installation

1. Copy the `custom_components/selfmon` folder to your Home Assistant `config/custom_components/` directory

2. Restart Home Assistant

3. Go to **Settings** > **Devices & Services** > **Add Integration**

4. Search for "Honeywell Galaxy Alarm" and select it

### HACS Installation (Future)

This integration may be added to HACS in the future.

## Configuration

### Step 1: Module Discovery

When you add the integration, it will automatically search for VMOD modules on your MQTT broker by subscribing to `selfmon/vmod.#`.

- If **one module** is found, it proceeds automatically
- If **multiple modules** are found, you'll select which one to configure
- If **no modules** are found, you can enter the path manually (e.g., `selfmon/vmod.010aa1`)

### Step 2: Output Sensors

You'll be asked if you want to enable output sensors (Siren, Intruder, Fire, Set status). 

- Select **Yes** to configure each output sensor individually
- Select **No** to skip outputs entirely

### Step 3: Configure Zone Sensors

For each discovered zone sensor, you can:
- **Enable/Disable**: Choose whether to add this sensor to Home Assistant
- **Name**: Set a custom name (e.g., "Front Door", "Hallway Motion")
- **Device Class**: Select the appropriate type:
  - `door` - Door/window contact
  - `motion` - PIR motion sensor
  - `smoke` - Smoke detector
  - `safety` - Break glass, panic button
  - `window` - Window contact
  - `garage_door` - Garage door
  - `vibration` - Shock/vibration sensor
  - `tamper` - Tamper switch

### Automatic Sensors

The following sensors are **always enabled** and don't require configuration:
- Temperature sensor
- Keypad Line 1
- Keypad Line 2
- Module Version

## MQTT Topics

The integration subscribes to these topic patterns (example using module `010aa1`):

| Topic Pattern | Type | Description |
|--------------|------|-------------|
| `selfmon/vmod.010aa1/prio/inputs/read/#` | Binary Sensor | Physical RIO zone inputs |
| `selfmon/vmod.010aa1/vrio/inputs/read/#` | Binary Sensor | Virtual RIO zone inputs |
| `selfmon/vmod.010aa1/prio/outputs/#` | Sensor | Physical RIO outputs (if enabled) |
| `selfmon/vmod.010aa1/vrio/outputs/#` | Sensor | Virtual RIO outputs (if enabled) |
| `selfmon/vmod.010aa1/temperature` | Sensor | Module temperature |
| `selfmon/vmod.010aa1/vkp/display/line1` | Sensor | Keypad display line 1 |
| `selfmon/vmod.010aa1/vkp/display/line2` | Sensor | Keypad display line 2 |
| `selfmon/vmod.010aa1/version` | Sensor | Module firmware version |

## Troubleshooting

### No modules discovered

1. Check that your VMOD is online and connected to the MQTT broker
2. Use MQTT Explorer to verify topics are being published under `selfmon/vmod.XXXXXX`
3. Ensure the MQTT integration is configured in Home Assistant
4. Try entering the module path manually

### No sensors discovered

1. Verify the VMOD is publishing zone data to MQTT
2. Check that zones are configured on your alarm panel
3. Wait for zone state changes to trigger MQTT publishes

### Sensors not updating

1. Verify the VMOD is publishing to MQTT (use MQTT Explorer)
2. Check that zone states are changing on your alarm panel
3. Review Home Assistant logs for any errors

## Reconfiguration

To reconfigure sensors after initial setup:

1. Go to **Settings** > **Devices & Services**
2. Find "Honeywell Galaxy Alarm" and click **Configure**
3. Follow the sensor configuration steps again

## Support

For issues related to:
- **This integration**: Open an issue on the GitHub repository
- **SelfMon VMOD**: Visit [selfmon.uk](http://www.selfmon.uk)
- **Galaxy alarm panels**: Contact Honeywell support

## License

This integration is provided as-is for personal use with your own alarm system.

## Custom Icon

To add a custom icon for this integration, place a `icon.png` (256x256 recommended) or `icon@2x.png` file in the `custom_components/selfmon/` folder. The integration will use the Honeywell branding by default if available through Home Assistant's brand repository.
