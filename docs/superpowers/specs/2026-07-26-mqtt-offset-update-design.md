# MQTT-driven offset update — design

## Purpose

Roof and tank temperature calibration offsets are currently read once at
startup from `RoofOffset.txt` / `TankOffset.txt` (via
`OffsetCalculationAndStorage.read_and_convert`) and never change again until
the process restarts. This feature lets a user push a new offset value over
MQTT at runtime; the running process applies it immediately and persists it
to the corresponding text file so it survives the next restart.

## Architecture

Two new MQTT subscriptions are added:

- `tempRoofOffsetByUser`
- `tempTankOffsetByUser`

Each topic gets its own callback registered via
`mqttc.message_callback_add(topic, handler)`. A handler parses the message
payload as a plain float string (matching the existing text-file format),
and on success:

1. Updates the corresponding in-memory global (`RoofOffset` / `TankOffset`)
   so the very next ADC sample uses the new value.
2. Persists the value via the existing `OffsetCalculationAndStorage.write_value()`
   to the corresponding offset file.

On a parse failure (payload isn't a valid float), the handler prints an
error message and leaves both the in-memory value and the file untouched —
mirroring the existing error style in `read_and_convert`.

`mqttc.loop_start()` is added after `mqttc.connect()`. Today nothing runs
paho's network loop — `publish()` calls happen to work without it, but a
subscription's callback will never fire without a running loop. `loop_start()`
runs the loop in a background thread, so the existing `time.sleep`-based
main loop in `HeatCollectorMain.main()` doesn't need restructuring.

## Components

**`HeatCollectorMain.py`**

- New constants:
  - `MQTT_ROOFOFFSET_TOPIC = "tempRoofOffsetByUser"`
  - `MQTT_TANKOFFSET_TOPIC = "tempTankOffsetByUser"`
  - `ROOF_OFFSET_FILE = "RoofOffset.txt"`
  - `TANK_OFFSET_FILE = "TankOffset.txt"`

  The file-path constants replace the inline string literals currently used
  only at startup (`read_and_convert("RoofOffset.txt")` /
  `read_and_convert("TankOffset.txt")`); the same paths are now needed again
  on the write side, so a shared constant avoids the two spots drifting out
  of sync.

- New handler functions, defined alongside the existing `on_connect` /
  `on_publish` handlers:

  ```python
  def on_roof_offset_message(client, userdata, msg):
      global RoofOffset
      try:
          new_offset = float(msg.payload.decode().strip())
      except ValueError:
          print("Error: received roof offset payload is not a valid number.")
          return
      RoofOffset = new_offset
      OffsetCalculationAndStorage.write_value(RoofOffset, ROOF_OFFSET_FILE)

  def on_tank_offset_message(client, userdata, msg):
      global TankOffset
      try:
          new_offset = float(msg.payload.decode().strip())
      except ValueError:
          print("Error: received tank offset payload is not a valid number.")
          return
      TankOffset = new_offset
      OffsetCalculationAndStorage.write_value(TankOffset, TANK_OFFSET_FILE)
  ```

- In `main()`, after `mqttc.connect(...)`:

  ```python
  mqttc.subscribe(MQTT_ROOFOFFSET_TOPIC)
  mqttc.subscribe(MQTT_TANKOFFSET_TOPIC)
  mqttc.message_callback_add(MQTT_ROOFOFFSET_TOPIC, on_roof_offset_message)
  mqttc.message_callback_add(MQTT_TANKOFFSET_TOPIC, on_tank_offset_message)
  mqttc.loop_start()
  ```

**`OffsetCalculationAndStorage.py`**

No changes — `write_value(tempOffset, file_path)` already does exactly what's
needed for persistence.

## Data flow

1. User publishes a plain numeric string, e.g. `"2.5"`, to
   `tempRoofOffsetByUser`.
2. paho's background loop thread (started by `loop_start()`) invokes
   `on_roof_offset_message`.
3. Payload parses successfully as float → global `RoofOffset` updated
   immediately (next ADC sample in the main loop uses it) → value written to
   `RoofOffset.txt`.
4. Tank path (`tempTankOffsetByUser` → `on_tank_offset_message` →
   `TankOffset` / `TankOffset.txt`) is symmetric.

## Error handling

- Non-numeric or empty payload: handler prints an error message, does not
  touch the in-memory offset or the file. No exception propagates — this is
  an unattended process controlling a physical pump relay, so a bad message
  must never crash it or leave state half-updated.
- No plausibility bounds are placed on the accepted offset value (e.g.
  rejecting an unreasonably large offset) — out of scope for this feature;
  the user is trusted to publish sane values, matching the trust level
  already given to the static offset text files.

## Testing

No automated test suite exists in this repo. Verification plan:

- The float-parsing/update logic is a pure function of a payload string and
  can be sanity-checked standalone without hardware or a real broker.
- Full end-to-end behavior (subscribe actually receiving messages via
  `loop_start()`, file writes landing correctly) needs a real MQTT broker
  and ideally the target Raspberry Pi — not verifiable in this environment.
  This is why the work is on its own branch (`feature/mqtt-offset-update`):
  it can be deployed and tested against the target/broker independently of
  the already-working `main` branch, and rolled back cleanly if it doesn't
  behave as expected on hardware.

## Out of scope

- Validating/bounding the numeric offset value.
- Changing the payload format to JSON.
- Any change to the plausibility-checking stub
  (`MeasurementDataPlausibilityChecker.py`) — unrelated pre-existing gap.
