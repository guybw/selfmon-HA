# Changelog

All notable changes to this integration are documented in this file.

## [1.2.3] - 2026-09-05

### Fixed

- **Issue:** Home Assistant rejected some sensor/binary_sensor entities at startup with errors like `Platform selfmon does not generate unique IDs. ID selfmon_010ff8_output_1024 already exists`. Zone-input and output sensors are discovered from two independent MQTT buses (`prio` and `vrio`), which can reuse the same numeric zone/output ID on each bus. Since `unique_id` was built only from the hardware ID and that numeric ID, two different physical sensors could collide on the same `unique_id`, causing the second one to be silently dropped.
- `unique_id` for zone-input and output entities now also includes the source bus (`prio`/`vrio`), guaranteeing a deterministic, unique ID per physical sensor.

### Notes

- Because affected entities' `unique_id` values changed, previously colliding/dropped entities will register as new entities after upgrading. Any stale/orphaned entries left behind for the same zone or output can be safely removed from Settings → Devices & Services → Entities.
