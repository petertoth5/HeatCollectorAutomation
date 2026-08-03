# RESUME.md

## Most recent change

Two follow-ups on `feature/mqtt-reference-offset-correction` (still the same
branch — no new branch for this work, per explicit user instruction)
after the offset state-publish feature landed:

1. **Fixed a self-inflicted HA outage.** The final-review fix wave had
   added/corrected `unique_id`s on several MQTT entities in
   `HAConfigurationYAML/configuration.yaml` (fixed a typo on
   `TemperatureRoofSensor`'s `unique_id`, added new ones to
   `SunCollectorPowerSensor`/`Roof Offset`/`Tank Offset`). On the user's
   real Pi, `TemperatureRoofSensor` went unavailable in HA after deploying
   this — changing/adding a YAML MQTT entity's `unique_id` makes HA treat
   it as a brand-new registry entry, orphaning the one already bound to the
   live dashboard and template sensors. All four `unique_id` changes were
   reverted (commit `45e7aaa`) back to their original pre-session values/
   absence. **Lesson: don't add or "fix" a `unique_id` on an MQTT YAML
   entity that already has real dashboard/automation history — it isn't a
   pure cosmetic change, it's an identity change.**
2. **Added periodic offset republish** (commit `c0e73fa`, user request):
   `RoofOffsetCurrent`/`TankOffsetCurrent` previously only published on
   MQTT (re)connect and on offset change. Now also republished every ~4s
   in the main sampling loop, same cadence as `TemperatureRoof`/
   `TemperatureTank`, so the HA dashboard stays current even if a broker
   restart drops the retained message without the Pi itself reconnecting.

**On-target verification: passed.** After root-causing an initial "offsets
not updating on the HA dashboard" report (turned out to be a stale/not-
actually-updated deployment on the Pi, not a code bug — confirmed via
`mosquitto_sub` showing nothing at all on the new topics while
`TemperatureRoof`/`TemperatureTank` kept updating fine, which isolated it
to a deployment issue rather than a runtime exception), the user redeployed
and confirmed **everything is working correctly now**: offsets publish and
update on the HA dashboard as expected.

Full history: `docs/superpowers/specs/2026-08-03-mqtt-offset-state-publish-design.md`,
`docs/superpowers/plans/2026-08-03-mqtt-offset-state-publish.md`. Earlier
feature (reference-temperature offset correction) history is under the
`2026-07-28-mqtt-reference-offset-correction` spec/plan files.

Per explicit user instruction for this session: every commit was shown as
a diff and only made after explicit approval — no auto-committing.

## Current state

- Branch `feature/mqtt-reference-offset-correction` carries **two**
  features plus fix waves, all on one branch (per explicit instruction not
  to branch separately for the second feature):
  1. MQTT reference-temperature offset correction (`tempRoofReference`/
     `tempTankReference` → auto-adjusts `RoofOffset`/`TankOffset`).
  2. MQTT current-offset state publish (`RoofOffsetCurrent`/
     `TankOffsetCurrent`, retained, published on connect/reconnect, on
     every offset change, and periodically every ~4s).
  16 commits ahead of `main`, ending at `c0e73fa`. **Confirmed working by
  the user on real hardware** (HA dashboard shows live, updating offset
  values). Not yet merged to `main`, not yet pushed.
- **Push still blocked in this environment:** this sandbox has no SSH key
  for `git@github.com:petertoth5/HeatCollectorAutomation.git`. **The user
  has said they will push and open the PR themselves.**
- Branch `fix/on-connect-rc-check` (the standalone single-commit rc-check
  fix, content fully duplicated into this branch) was deleted this
  session — no longer exists locally.
- No known regressions. No open Critical/Important findings from either
  feature's final review. The one real production incident this session
  (the `unique_id` orphaning) has been fixed and confirmed resolved by the
  user ("now everything is fine").
- Pre-existing open items (unchanged, not addressed by this work):
  `MeasurementDataPlausibilityChecker.py` is still an empty stub;
  `HATemplates/Sensor value difference.yaml` still has garbled quote
  characters; stale branches `improve_code_quality` and
  `fix/issue-4-global-state` still exist (remote-only, not fetched into
  this local clone); `main` still has no branch protection ruleset; no
  automated test suite; the `sonos:` block in `configuration.yaml` may use
  a superseded YAML-based integration style, left untouched (never
  confirmed broken, and removing a live integration's config without
  confirmation would be a destructive guess).

## Continuation prompt

Paste this into a new session to continue:

> Read README.md and CLAUDE.md. Branch `feature/mqtt-reference-offset-correction`
> (ends at `c0e73fa`) has two features — MQTT reference-temperature offset
> correction, and MQTT current-offset state publish
> (`RoofOffsetCurrent`/`TankOffsetCurrent`, retained, published on
> connect/reconnect, on every offset change, and periodically every ~4s).
> **The user has confirmed on real hardware that everything works
> correctly** (HA dashboard shows live offset values updating). Branch is
> not yet merged to `main`, not yet pushed — the user said they'll push and
> open the PR themselves (this sandbox has no SSH key for the
> `git@github.com:petertoth5/...` remote).
> One incident this session worth knowing about: a `unique_id` "typo fix"
> and additions on a few MQTT entities in
> `HAConfigurationYAML/configuration.yaml` orphaned a live HA entity
> (`TemperatureRoofSensor` went unavailable) — changing/adding a
> `unique_id` on an MQTT YAML entity that already has dashboard/automation
> history makes HA treat it as a new entity. All four `unique_id` changes
> were reverted (commit `45e7aaa`) and the user confirmed things are fine
> again. **Don't reintroduce `unique_id` changes on entities that already
> have production history without asking first.**
> Branch `fix/on-connect-rc-check` was deleted this session (its content
> was already fully duplicated into this branch).
> Next step: push to `origin` and open the PR against `main`, then
> `superpowers:finishing-a-development-branch`.
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
> explicit instruction this session that should carry forward unless the
> user says otherwise) and update RESUME.md before finishing.
