# GEO heat-pump and whole-home EMS meter support

This contribution extends Euros OS without replacing its existing MQTT integration.

## GEO-specific entities

- Detect GEO-specific behavior from the stored `device_type == "FriskoGEO"`.
- Keep the existing entity IDs/unique IDs while filtering out readings not present in observed GEO telemetry.
- Map GEO heating/cooling and domestic hot water operating states using validated state flags. Missing or invalid inputs yield an unknown state instead of a fabricated idle reading.
- Add model-specific labels and ground/upper-source temperature delta sensors.
- Read the controller's software version from reported MQTT fields.
- Preserve the existing behavior for non-GEO device models.

## Modes and safety

- Reflect AUTO/EMS/TIME/AWAY/OFF using device data where verified.
- The EMS selection is visible in GEO mode reporting, but **writing EMS** and switching **from EMS to AUTO** via undocumented MQTT commands are intentionally blocked.
- This PR does not add unverified control commands, or modify the existing MQTT topic setup.

## Whole-home EMS meter

- Parse a `Name="METER_1", Type="METER"` device embedded in the existing `/Dev` MQTT payload.
- Expose **33 read-only instantaneous/cumulative sensors** (power, import/export energy, phase voltage/current, frequency, power factors and diagnostic fields).
- Add **two daily import/export energy sensors**, based on physical cumulative meter totals; their current-day state is restored after Home Assistant restarts.
- Associate the logical EMS meter with its parent heat-pump device by the supported `via_device_id` registry field.
- Preserve signed meter power readings and keep unavailable/invalid measurements distinct from zero.

**Important:** The EMS meter represents the **whole home's grid connection**, not the electricity consumption of the heat pump. It should not be labeled as pump energy usage.

## Compatibility and testing

- No external dependencies added.
- Existing `unique_id` generation and MQTT control paths are preserved.
- Tested on a physical GEO heat-pump installation with Home Assistant Core 2026.10.4; the companion deprecation fix `via_device_id` eliminated the corresponding warning.
- Dependency-free regression tests are included in `tests/test_geo.py` and `tests/test_ems.py`. Other hardware models have not been comprehensively validated.

This PR deliberately does **not** include the separate upstream NumberEntity deprecation fix proposed in [PR #3](https://github.com/McKoPcIu/EurosOS/pull/3).
