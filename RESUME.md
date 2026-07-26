# RESUME.md

## Most recent change

MQTT-driven offset updates feature, merged to `main` (was branch
`feature/mqtt-offset-update`, PR opened/merged by the user on GitHub; local
`main` confirmed synced at commit `b0705d1`):

- `src/main/HeatCollectorMain.py` subscribes to `tempRoofOffsetByUser` and
  `tempTankOffsetByUser`. Each topic has its own `message_callback_add`
  handler (`on_roof_offset_message`, `on_tank_offset_message`) that parses
  the payload as a float, updates the in-memory `RoofOffset`/`TankOffset`
  global immediately, and persists it via
  `OffsetCalculationAndStorage.write_value()` to `RoofOffset.txt`/
  `TankOffset.txt`. Invalid or non-finite (`nan`/`inf`) payloads are logged
  and ignored — no crash, no partial update.
- Added `mqttc.loop_start()` after `mqttc.connect()` — previously nothing ran
  paho's network loop, so subscriptions would never have delivered a message.
- A final whole-branch review caught a pre-existing, previously-dormant bug
  this feature activated: `on_connect` had the wrong arity for paho-mqtt
  2.0's VERSION1 API. `loop_start()` would have hit it immediately, silently
  killing the MQTT loop thread ~1 minute after startup (no offset delivery,
  no keepalive, so the broker drops the connection and `RelayHandling`'s
  Shelly relay commands would silently fail while the process kept running).
  Fixed, along with moving offset-topic subscriptions into `on_connect` (so
  they survive auto-reconnects) and adding `math.isfinite()` rejection.
- **On-target verification: passed.** User confirmed on the real Raspberry
  Pi / real MQTT broker: publishing to either topic updates the running
  offset and the corresponding text file; normal temperature sampling and
  relay control are unaffected by `loop_start()` / `on_connect`'s
  re-subscribe.
- `README.md` updated with a new "Adjusting sensor calibration offsets via
  MQTT" section (topic table, `mosquitto_pub` examples, payload/error
  behavior).
- Full history: spec `docs/superpowers/specs/2026-07-26-mqtt-offset-update-design.md`,
  plan `docs/superpowers/plans/2026-07-26-mqtt-offset-update.md`.

Also discussed (not implemented): adding a Home Assistant dashboard control
for the offsets via an `mqtt: number:` entity with `command_topic` set to
`tempRoofOffsetByUser`/`tempTankOffsetByUser`. Noted caveat: the controller
never publishes the *current* offset back to MQTT, so such a HA entity would
be write-only (won't reflect the real applied value after a HA restart)
unless a `state_topic` publish is added on the Python side too — this was
left as an open option, not decided or built.

## Current state

- `main` has the offset-update feature merged and verified on target
  hardware. No known regressions.
- Two Minor items from the final review, still open, not blockers:
  `on_connect` doesn't check `rc` before subscribing (a refused CONNACK logs
  a false "Connected" and the subscribes silently no-op); an offset change
  takes ~30s to fully propagate since the 200-sample circular buffers retain
  readings computed with the old offset.
- Possible next step (discussed, undecided): HA dashboard `number` entity for
  live offset adjustment, and whether to add a `state_topic` publish of the
  current offset so the HA entity can reflect real device state.
- Pre-existing open items (unchanged, not addressed by this work):
  `MeasurementDataPlausibilityChecker.py` is still an empty stub;
  `HATemplates/Sensor value difference.yaml` still has garbled quote
  characters; stale branches `improve_code_quality` and
  `fix/issue-4-global-state` still exist; `main` still has no branch
  protection ruleset; no automated test suite.

## Continuation prompt

Paste this into a new session to continue:

> Read README.md and CLAUDE.md. `main` has the MQTT-driven offset-update
> feature merged and verified on target hardware (topics
> `tempRoofOffsetByUser`/`tempTankOffsetByUser`, handlers in
> `src/main/HeatCollectorMain.py`; see
> `docs/superpowers/specs/2026-07-26-mqtt-offset-update-design.md` and
> `docs/superpowers/plans/2026-07-26-mqtt-offset-update.md` for history).
> Two Minor items are open from the final review (not blockers): no `rc`
> check in `on_connect` before subscribing, and offset changes take ~30s to
> fully propagate through the circular buffers.
> Last session also discussed (but did not build) a Home Assistant dashboard
> `number` entity for adjusting the offsets live via
> `command_topic: tempRoofOffsetByUser`/`tempTankOffsetByUser` in
> `HAConfigurationYAML/configuration.yaml`. It would be write-only as-is —
> the Python side never publishes the current offset back to MQTT — so if
> asked to build this, first ask whether a `state_topic` publish (current
> `RoofOffset`/`TankOffset` value, published at startup and/or after each
> update) should be added so the HA entity reflects real device state, or
> whether write-only is acceptable.
> Pre-existing open items, unchanged: `MeasurementDataPlausibilityChecker.py`
> is still an empty stub; `HATemplates/Sensor value difference.yaml` still
> has garbled quote characters; stale branches `improve_code_quality` and
> `fix/issue-4-global-state` still exist; `main` has no branch protection
> ruleset; no automated test suite exists (verification is via standalone
> scripts, not pytest). Follow CLAUDE.md's working principles (surgical
> changes, ask before assuming on hardware/threshold specifics) and update
> RESUME.md before finishing.
