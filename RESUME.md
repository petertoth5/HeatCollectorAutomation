# RESUME.md

## Most recent change

Merged `feature/mqtt-reference-offset-correction` into `main` locally
(fast-forward, `main` now at `7cf44cc`). The user has confirmed on real
hardware that everything works correctly end-to-end. This branch carried
two features, both now on `main`:

1. **MQTT reference-temperature offset correction** — new topics
   `tempRoofReference`/`tempTankReference` carry a reference temperature
   from an independent external sensor; `on_roof_reference_message`/
   `on_tank_reference_message` in `src/main/HeatCollectorMain.py` use
   `OffsetCalculationAndStorage.compute_corrected_offset()` to recompute
   `RoofOffset`/`TankOffset` so the Pi's own reading converges to the
   reference. Guards: reject non-finite or out-of-plausible-range
   (-20..120°C) reference values; skip if no temperature average has been
   computed yet (`RoofTemp`/`TankTemp` still `None`); rate-limited to one
   accepted correction per sensor per 30s (matches the 200-sample buffer's
   convergence time).
2. **MQTT current-offset state publish** — new retained topics
   `RoofOffsetCurrent`/`TankOffsetCurrent` report the currently-applied
   offset back to MQTT, published on every MQTT (re)connect, on every
   accepted offset change (manual or reference-corrected), and
   periodically every ~4s (same cadence as `TemperatureRoof`/
   `TemperatureTank`). `HAConfigurationYAML/configuration.yaml`'s existing
   `Roof Offset`/`Tank Offset` `number` entities got a `state_topic`
   pointing at these, so the HA dashboard always reflects the real applied
   value regardless of what last changed it.

Along the way this session also fixed/reverted a self-inflicted issue:
adding/correcting `unique_id`s on a few MQTT entities in
`configuration.yaml` (meant as a cosmetic typo fix) orphaned the live
`TemperatureRoofSensor` entity in HA, since changing a YAML MQTT entity's
`unique_id` makes HA treat it as a new registry entry. Reverted. **Lesson:
don't add or "fix" a `unique_id` on an MQTT YAML entity that already has
real dashboard/automation history.**

Full history: `docs/superpowers/specs/2026-07-28-mqtt-reference-offset-correction-design.md`
+ `docs/superpowers/plans/2026-07-28-mqtt-reference-offset-correction.md`
(feature 1), `docs/superpowers/specs/2026-08-03-mqtt-offset-state-publish-design.md`
+ `docs/superpowers/plans/2026-08-03-mqtt-offset-state-publish.md`
(feature 2).

Per explicit user instruction for this session: every commit was shown as
a diff and only made after explicit approval — no auto-committing.

## Current state

- `main` is at `7cf44cc`, containing both features above, merged locally
  (fast-forward from `feature/mqtt-reference-offset-correction`).
  **Confirmed working by the user on real hardware.**
- **Not yet pushed to `origin`.** This sandbox has no SSH key for
  `git@github.com:petertoth5/HeatCollectorAutomation.git`
  (`Permission denied (publickey)` on both `git pull`/`git push` all
  session). **The user will push `main` to `origin` themselves.**
- Local branch `feature/mqtt-reference-offset-correction` still exists
  (not deleted) — git refused a plain `git branch -d` because it isn't
  merged into `origin`'s copy of that branch (nothing's been pushed yet).
  Safe to delete once `main` is pushed and the user confirms the branch is
  no longer needed; not deleted preemptively to avoid losing anything
  before the push happens.
- Branch `fix/on-connect-rc-check` (the standalone rc-check fix, content
  fully duplicated into `main` via the merge) was deleted earlier this
  session — no longer exists locally.
- No known regressions, no open Critical/Important findings from either
  feature's final review.
- Pre-existing open items (unchanged, not addressed by this work):
  `MeasurementDataPlausibilityChecker.py` is still an empty stub;
  `HATemplates/Sensor value difference.yaml` still has garbled quote
  characters; stale branches `improve_code_quality` and
  `fix/issue-4-global-state` still exist (remote-only, not fetched into
  this local clone); `main` still has no branch protection ruleset; no
  automated test suite; the `sonos:` block in `configuration.yaml` may use
  a superseded YAML-based integration style, left untouched (never
  confirmed broken).

## Continuation prompt

Paste this into a new session to continue:

> Read README.md and CLAUDE.md. `main` is at `7cf44cc` and contains two
> merged features: MQTT reference-temperature offset correction
> (`tempRoofReference`/`tempTankReference`) and MQTT current-offset state
> publish (`RoofOffsetCurrent`/`TankOffsetCurrent`, retained, published on
> connect/reconnect, on every offset change, and periodically every ~4s).
> **The user has confirmed on real hardware that everything works
> correctly.** `main` has NOT yet been pushed to `origin` — this sandbox
> has no SSH key for the remote, so the user needs to `git push origin
> main` themselves.
> Local branch `feature/mqtt-reference-offset-correction` still exists
> (git wouldn't let a plain `-d` delete it since it's not merged into
> `origin`'s copy) — safe to delete once the user confirms `main` is
> pushed and the branch isn't needed.
> One incident worth knowing about from this session: adding/correcting a
> `unique_id` on a few MQTT entities in `HAConfigurationYAML/configuration.yaml`
> orphaned a live HA entity (`TemperatureRoofSensor` went unavailable) —
> changing/adding a `unique_id` on an MQTT YAML entity that already has
> dashboard/automation history makes HA treat it as a new entity. Reverted
> and confirmed fixed. **Don't reintroduce `unique_id` changes on entities
> with production history without asking first.**
> Full spec/plan history: `docs/superpowers/specs/` and
> `docs/superpowers/plans/`, both `2026-07-28-mqtt-reference-offset-correction-*`
> and `2026-08-03-mqtt-offset-state-publish-*` files.
> Pre-existing open items, unchanged: `MeasurementDataPlausibilityChecker.py`
> is still an empty stub; `HATemplates/Sensor value difference.yaml` still
> has garbled quote characters; stale branches `improve_code_quality` and
> `fix/issue-4-global-state` still exist (remote-only); `main` has no
> branch protection ruleset; no automated test suite exists (verification
> is via standalone scripts, not pytest); the `sonos:` block in
> `configuration.yaml` may use a superseded YAML-based integration style,
> left untouched pending user confirmation it's still needed. Follow
> CLAUDE.md's working principles (surgical changes, ask before assuming on
> hardware/threshold specifics, **ask before committing anything** — an
> explicit instruction in the prior session that should carry forward
> unless the user says otherwise) and update RESUME.md before finishing.
