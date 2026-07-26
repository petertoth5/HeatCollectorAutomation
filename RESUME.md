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
- Final whole-branch review caught a pre-existing, previously-dormant bug
  this feature would have activated: `on_connect(mosq, obj, rc)` had the
  wrong arity for paho-mqtt 2.0's VERSION1 API (needs 4 args). Nothing ran
  paho's network loop before this branch, so it never mattered; this
  branch's `loop_start()` would have hit it immediately, silently killing
  the MQTT loop thread ~1 minute after startup (no offset delivery, no
  keepalive, so the broker drops the connection and every later
  `publish()` — including `RelayHandling`'s Shelly relay commands —
  silently fails while the process keeps running). Fixed in commit
  `02e7f99`, along with two related issues: offset-topic subscriptions
  moved into `on_connect` (so they survive auto-reconnects, previously
  they'd have been lost after any reconnect since `clean_session=True` is
  the default), and both handlers now reject non-finite (`nan`/`inf`)
  payloads via `math.isfinite()`, not just non-numeric ones. Re-reviewed
  clean after the fix.

## Current state

- Work is on branch `feature/mqtt-offset-update`, not yet merged to `main`.
  `main` remains at tag `v1.1.0` (commit `ba62c6b`), unaffected and known-good.
- **PR status: not yet opened.** Push failed from the agent session
  (`Permission denied (publickey)` — no working SSH key in that
  environment); the user is pushing and opening the PR manually.
  **⚠️ Update this line with the PR URL once it exists**, so the next
  session doesn't have to search for it.
- **On-target verification: passed.** User confirmed on the real Raspberry
  Pi / real MQTT broker: publishing to `tempRoofOffsetByUser` /
  `tempTankOffsetByUser` correctly updates the running offset and the
  corresponding text file, and normal temperature sampling / relay control
  is unaffected by the added `loop_start()` background thread and the
  `on_connect` re-subscribe behavior. The prior "not yet tested on target"
  blocker is now cleared — remaining work before merge is just the Minor
  items below (optional) and the PR itself.
- Two Minor items from the final review, not yet addressed (not blockers):
  `on_connect` doesn't check `rc` before subscribing (a refused CONNACK
  logs a false "Connected" and the subscribes silently no-op); an offset
  change takes ~30s to fully take effect since the 200-sample circular
  buffers still hold readings computed with the old offset. `README.md`
  also hasn't been updated to list the two new MQTT topics.
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
> A final review caught and fixed (commit `02e7f99`) a dormant `on_connect`
> arity bug that `loop_start()` would have activated, plus moved offset
> subscriptions into `on_connect` (survive reconnects) and added
> `nan`/`inf` rejection on offset payloads.
> **PR link: <fill in once opened — check if one already exists for
> `feature/mqtt-offset-update` before assuming it's still missing>.**
> On-target verification (real Pi, real MQTT broker) has **passed**: the
> user confirmed publishing to either topic updates the running offset and
> text file, and normal temperature sampling / relay control is unaffected
> by `loop_start()` / `on_connect`'s re-subscribe. That was previously the
> main blocker before merging — it's now cleared.
> Two Minor items are still open from the final review (not blockers): no
> `rc` check in `on_connect` before subscribing, and offset changes take
> ~30s to fully propagate since the circular buffers retain old-offset
> readings; README.md also still needs the two new topics added to its
> topic list. `main` is unaffected and sits at tag `v1.1.0` (commit
> `ba62c6b`) as a safe fallback. No test suite exists in this repo —
> verification is via standalone scripts, not pytest. Follow CLAUDE.md's
> working principles (surgical changes, ask before assuming on
> hardware/threshold specifics) and update RESUME.md again before finishing.
