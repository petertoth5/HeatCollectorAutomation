# RESUME.md

## Most recent change

Implemented MQTT-driven offset updates on branch `feature/mqtt-offset-update`
(spec: `docs/superpowers/specs/2026-07-26-mqtt-offset-update-design.md`, plan:
`docs/superpowers/plans/2026-07-26-mqtt-offset-update.md`):

- `src/main/HeatCollectorMain.py` now subscribes to `tempRoofOffsetByUser` and
  `tempTankOffsetByUser`. Each topic has its own `message_callback_add`
  handler (`on_roof_offset_message`, `on_tank_offset_message`) that parses
  the payload as a float, updates the in-memory `RoofOffset`/`TankOffset`
  global immediately, and persists it via the existing
  `OffsetCalculationAndStorage.write_value()` to `RoofOffset.txt`/
  `TankOffset.txt`. Invalid (non-numeric) payloads are logged and ignored —
  no crash, no partial update.
- Added `mqttc.loop_start()` after `mqttc.connect()`. Previously nothing ran
  paho's network loop at all; `publish()` happened to work without it, but
  subscriptions would never have delivered a message.
- New constants: `MQTT_ROOFOFFSET_TOPIC`, `MQTT_TANKOFFSET_TOPIC`,
  `ROOF_OFFSET_FILE`, `TANK_OFFSET_FILE` (the latter two replace inline
  string literals previously used only at startup).
- Verified with a standalone script (not committed) that stubs the
  `ADCDACPi` import (its `spidev` dependency is Pi-only) to exercise the
  real handler functions directly: valid payloads update both the global
  and the file, invalid payloads change neither. Full subscribe/publish
  behavior against a real broker, and behavior on real ADC hardware, is
  **not yet verified** — needs testing on the target Raspberry Pi.

## Current state

- Work is on branch `feature/mqtt-offset-update`, not yet merged to `main`.
  `main` remains at tag `v1.1.0` (commit `ba62c6b`), unaffected and known-good.
- This feature has not been tested against a live MQTT broker or on the
  target Pi. Before merging: confirm a message published to
  `tempRoofOffsetByUser`/`tempTankOffsetByUser` on the real broker actually
  updates the running process's offset and the text file, and that normal
  sensor sampling/relay control is unaffected by the added `loop_start()`
  background thread.
- Pre-existing open items (unchanged, not addressed by this work):
  `MeasurementDataPlausibilityChecker.py` is still an empty stub;
  `HATemplates/Sensor value difference.yaml` still has garbled quote
  characters; stale branches `improve_code_quality` and
  `fix/issue-4-global-state` still exist; `main` still has no branch
  protection ruleset.

## Continuation prompt

Paste this into a new session to continue:

> Read README.md and CLAUDE.md, then read
> `docs/superpowers/specs/2026-07-26-mqtt-offset-update-design.md` and
> `docs/superpowers/plans/2026-07-26-mqtt-offset-update.md`. Branch
> `feature/mqtt-offset-update` implements MQTT-driven roof/tank offset
> updates (topics `tempRoofOffsetByUser`/`tempTankOffsetByUser`, handlers
> `on_roof_offset_message`/`on_tank_offset_message` in
> `src/main/HeatCollectorMain.py`, plus a new `mqttc.loop_start()` call).
> It has only been verified with a stubbed-`ADCDACPi` standalone script in
> a dev environment — never against a real MQTT broker or on the target
> Raspberry Pi. Before merging to `main`: test on-target that (1) publishing
> to either topic updates the running offset and the corresponding text
> file, (2) an invalid payload is logged and ignored without crashing,
> (3) normal temperature sampling / relay control / power-calc publishing
> still works correctly with the new `loop_start()` background thread
> running. `main` is unaffected and sits at tag `v1.1.0` (commit `ba62c6b`)
> as a safe fallback. No test suite exists in this repo — verification is
> via standalone scripts, not pytest. Follow CLAUDE.md's working principles
> (surgical changes, ask before assuming on hardware/threshold specifics)
> and update RESUME.md again before finishing.
