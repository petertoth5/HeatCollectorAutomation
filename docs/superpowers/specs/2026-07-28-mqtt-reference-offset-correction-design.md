# MQTT Reference-Temperature Offset Correction — Design

## Problem

The Pi's PTC1000 sensors need periodic recalibration against independent
"reference" temperature sensors (roof and tank). Today, calibration offsets
(`RoofOffset.txt`/`TankOffset.txt`) can only be set manually via
`tempRoofOffsetByUser`/`tempTankOffsetByUser` (a user-supplied absolute
offset value). This feature adds automatic offset correction: when a
reference temperature arrives from the other sensors over MQTT, the Pi
computes the offset needed to make its own reading match that reference,
and applies/persists it immediately.

## Scope

Two new MQTT topics, two new message handlers, reusing the existing
offset-storage plumbing. No changes to the main sampling loop, relay
control, or the existing manual offset topics.

## Topics

| Topic | Payload | Purpose |
|-------|---------|---------|
| `tempRoofReference` | plain float string, e.g. `24.3` | Roof reference temp from external sensor |
| `tempTankReference` | plain float string, e.g. `41.8` | Tank reference temp from external sensor |

## Behavior

On receipt of a valid reference temperature:

1. Parse payload as float. If not parseable, or not `math.isfinite()`
   (`nan`/`inf`/`-inf`), log an error and ignore the message — no state
   change. (Identical validation to `on_roof_offset_message`/
   `on_tank_offset_message`.)
2. Compute the new offset:

   ```
   new_offset = old_offset + (reference_temp - current_avg_temp)
   ```

   where `current_avg_temp` is the global `RoofTemp`/`TankTemp` (the
   200-sample circular-buffer average, already offset-corrected) and
   `old_offset` is the current global `RoofOffset`/`TankOffset`.

   Rationale: the buffer stores `raw_temp + old_offset` per sample, so
   `avg(raw_temp) = current_avg_temp - old_offset`. Solving for the offset
   that makes `avg(raw_temp) + new_offset == reference_temp` gives the
   formula above.
3. Update the global `RoofOffset`/`TankOffset` immediately — applied to the
   next raw sample read in the main loop.
4. Persist the new offset via `OffsetCalculationAndStorage.write_value()` to
   `RoofOffset.txt`/`TankOffset.txt`, so it survives a restart.

No plausibility bounds are applied to the reference value or the resulting
offset delta beyond the finite-float check — matches the existing manual
offset feature and this project's "no error handling for scenarios that
can't occur" principle.

## Interaction with existing manual offset feature

The two reference topics are additive and independent of
`tempRoofOffsetByUser`/`tempTankOffsetByUser`. Both write to the same
global/`.txt` file; whichever message (manual or reference) arrives last
wins. No special coordination between the two is implemented.

## Implementation

In `src/main/HeatCollectorMain.py`:

- Add `on_roof_reference_message(client, userdata, msg)` and
  `on_tank_reference_message(client, userdata, msg)`, following the same
  structure as the existing `on_roof_offset_message`/
  `on_tank_offset_message`.
- Register both via `mqttc.message_callback_add(...)` next to the existing
  registrations.
- Subscribe both topics in `on_connect`, alongside
  `MQTT_ROOFOFFSET_TOPIC`/`MQTT_TANKOFFSET_TOPIC` (so they survive
  reconnects, same reasoning as the existing subscriptions).
- Add `MQTT_ROOFREFERENCE_TOPIC = "tempRoofReference"` and
  `MQTT_TANKREFERENCE_TOPIC = "tempTankReference"` constants near the
  existing topic constants.

No new files, no new globals beyond what's already declared
(`RoofOffset`, `TankOffset`, `RoofTemp`, `TankTemp`).

## Error handling

Same as existing offset handlers: invalid payload → log and ignore, no
crash, no partial state change.

## Testing

No automated test suite in this repo. Verification is manual, on-target:
publish a test payload via `mosquitto_pub -h <broker> -t tempRoofReference
-m "<value>"` (and same for tank), confirm `RoofOffset.txt`/
`TankOffset.txt` update to the expected computed value, and confirm the
printed/published `RoofTemp`/`TankTemp` converge toward the reference value
over the next few sample cycles.

## Documentation

`README.md` gets a new section analogous to "Adjusting sensor calibration
offsets via MQTT", documenting the two reference topics, the correction
formula, and example `mosquitto_pub` commands.
