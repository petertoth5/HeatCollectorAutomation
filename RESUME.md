# RESUME.md

## Most recent change

Final-review fix wave for the "publish currently-applied offsets to MQTT"
feature, on `feature/mqtt-reference-offset-correction` (still the same
branch — no new branch was created for this feature per user instruction):

- `src/main/HeatCollectorMain.py` now publishes `RoofOffset`/`TankOffset`
  to two new **retained** MQTT topics, `RoofOffsetCurrent`/
  `TankOffsetCurrent`, so HA's dashboard reflects the real applied offset
  regardless of what last changed it (manual `tempRoofOffsetByUser`/
  `tempTankOffsetByUser`, automatic `tempRoofReference`/`tempTankReference`
  correction, or the value read from `RoofOffset.txt`/`TankOffset.txt` at
  startup).
- Publish happens in two places: (1) inside each of the four existing
  offset-change handlers, immediately after their existing `write_value()`
  call, using the handler's own `client` parameter (which *is* the
  connected `mqttc` instance); (2) in `on_connect`, on every (re)connect —
  **not** a one-shot startup call in `main()` as first implemented. A
  final-review finding caught that a one-shot startup publish would leave
  HA's dashboard stuck at a stale value forever after a broker restart
  (Mosquitto's default `persistence false` wipes the retained store), so
  the publish was moved into `on_connect` (guarded against `None`, in case
  an offset file was unreadable) to fire on every reconnect too.
- Reference-correction handlers now `round(..., 2)` the computed offset
  before applying/persisting/publishing it (previously could be e.g.
  `2.4000000000000004`).
- `HAConfigurationYAML/configuration.yaml`: the existing `Roof Offset`/
  `Tank Offset` `number` entities got a `state_topic` pointing at the two
  new topics (the `Roof Reference Temperature`/`Tank Reference
  Temperature` entities added earlier stay write-only — the Pi has no
  "current reference" concept to report back).
- Also fixed several pre-existing HA config issues that came along when
  the user re-downloaded `configuration.yaml` from the live Pi mid-session
  (not introduced by this feature, but caught by the final review and the
  user asked to fix them): `expire_after: 15` on `SunCollectorPowerSensor`
  was wrong (that topic only publishes every 300s, so the entity was
  flapping "unavailable" ~95% of the time) — changed to `330`;
  `unit_of_measurement: null` on the two temperature sensors and
  `SunCollectorPowerSensor` — set to `"°C"`/`"W"`; `SunCollectorPowerSensor`
  had `device_class: energy` for a watts value — changed to `power`; fixed
  a stray-`k` typo in a `unique_id`; added missing `unique_id` to three
  entities. Left the unrelated `sonos:` block alone — no evidence it's
  actually broken, and removing a live integration's config without
  confirmation would be a destructive, out-of-scope guess.
- Design/plan/history: `docs/superpowers/specs/2026-08-03-mqtt-offset-state-publish-design.md`,
  `docs/superpowers/plans/2026-08-03-mqtt-offset-state-publish.md`.

Per explicit user instruction for this session: every commit was shown to
the user as a diff and only made after their explicit "commit"/"ok" —
nothing was auto-committed by an implementer subagent. All implementer
subagents were told to leave their changes uncommitted; the controller
(this session) ran `git add`/`git commit` itself after approval.

## Current state

- Branch `feature/mqtt-reference-offset-correction` now carries **two**
  features plus their fix waves, all on the same branch (per explicit user
  instruction not to create a new branch for the second feature):
  1. MQTT reference-temperature offset correction (`tempRoofReference`/
     `tempTankReference` → auto-adjusts `RoofOffset`/`TankOffset`).
  2. MQTT current-offset state publish (`RoofOffsetCurrent`/
     `TankOffsetCurrent`, described above).
  13 commits ahead of `main`, ending at `ae97bc5`. **Not yet merged to
  `main`, not yet pushed, not yet verified on target hardware** — all
  verification so far is static (`ast.parse`) + manual code tracing; there
  is no MQTT broker or Raspberry Pi in this sandbox.
- **Push still blocked in this environment:** this sandbox has no SSH key
  for `git@github.com:petertoth5/HeatCollectorAutomation.git`
  (`Permission denied (publickey)` on both `git pull` and `git push`).
  **The user has said they will push themselves** — branch is fully
  committed and ready (`git push -u origin
  feature/mqtt-reference-offset-correction`, then open the PR).
- Separate, independent branch `fix/on-connect-rc-check` (single commit
  `d57b4e6`, forked from `main` before either feature) still exists
  locally, still unpushed. Its `on_connect` `rc != 0` guard was
  independently bundled into `feature/mqtt-reference-offset-correction`
  early on (commit `226a917`) and has since been extended further in that
  same function (the offset-republish-on-reconnect logic lives right after
  it). Once `feature/mqtt-reference-offset-correction` merges,
  `fix/on-connect-rc-check` is redundant and can be deleted.
- HA config note for the user: `HAConfigurationYAML/configuration.yaml` in
  this repo was last synced from a fresh download off the live Pi during
  this session (mid-session, replacing an earlier guess this agent had
  made) — the version in this repo now reflects that download plus the
  `state_topic`/`unique_id`/`unit_of_measurement`/`expire_after`/
  `device_class` fixes described above. **Push this file back to the Pi**
  along with the new HA `number` entities (`Roof Reference Temperature`,
  `Tank Reference Temperature`, and the `state_topic` additions on `Roof
  Offset`/`Tank Offset`) and restart HA for the changes to take effect.
- No known regressions. No open Critical/Important findings from either
  feature's final review — all were fixed and committed with the user's
  approval.
- Still open: on-target manual verification of both features (publish test
  payloads via `mosquitto_pub` to all four command/reference topics,
  confirm the `.txt` files and `RoofOffsetCurrent`/`TankOffsetCurrent`
  update correctly; confirm the HA dashboard cards track a broker restart
  correctly now that publish happens on every reconnect).
- Pre-existing open items (unchanged, not addressed by this work):
  `MeasurementDataPlausibilityChecker.py` is still an empty stub;
  `HATemplates/Sensor value difference.yaml` still has garbled quote
  characters; stale branches `improve_code_quality` and
  `fix/issue-4-global-state` still exist; `main` still has no branch
  protection ruleset; no automated test suite; the `sonos:` block in
  `configuration.yaml` was flagged by review as possibly using a superseded
  YAML-based integration style, left untouched pending user confirmation.

## Continuation prompt

Paste this into a new session to continue:

> Read README.md and CLAUDE.md. Branch `feature/mqtt-reference-offset-correction`
> (ends at `ae97bc5`) now has two features: (1) MQTT reference-temperature
> offset correction, and (2) MQTT current-offset state publish
> (`RoofOffsetCurrent`/`TankOffsetCurrent`, retained, republished on every
> MQTT reconnect as well as on every offset change). Both features' final
> whole-branch reviews are clean — see
> `docs/superpowers/specs/2026-08-03-mqtt-offset-state-publish-design.md`
> and `docs/superpowers/plans/2026-08-03-mqtt-offset-state-publish.md` for
> the second feature's history (the first feature's history is under the
> `2026-07-28-mqtt-reference-offset-correction` spec/plan files). All
> verification so far is static (`ast.parse`) + manual code tracing — no
> MQTT broker or Raspberry Pi in this sandbox. The user has said they will
> push and open the PR themselves (this sandbox has no SSH key for the
> `git@github.com:petertoth5/...` remote). `HAConfigurationYAML/configuration.yaml`
> was resynced from the live Pi mid-session and needs to be pushed back to
> the Pi (with the new `number` entities and `state_topic` additions) and
> HA restarted for the dashboard changes to take effect. There's also a
> separate unpushed branch `fix/on-connect-rc-check` (commit `d57b4e6`)
> whose content is now fully subsumed by `feature/mqtt-reference-offset-correction`
> — delete it once that branch merges. Next step: on-target manual
> verification once the user has hardware access (mosquitto_pub to all
> four command/reference topics, confirm .txt files and
> RoofOffsetCurrent/TankOffsetCurrent update, confirm HA dashboard survives
> a broker restart), then merge to `main` per
> superpowers:finishing-a-development-branch.
> Pre-existing open items, unchanged: `MeasurementDataPlausibilityChecker.py`
> is still an empty stub; `HATemplates/Sensor value difference.yaml` still
> has garbled quote characters; stale branches `improve_code_quality` and
> `fix/issue-4-global-state` still exist; `main` has no branch protection
> ruleset; no automated test suite exists (verification is via standalone
> scripts, not pytest); the `sonos:` block in `configuration.yaml` may use a
> superseded YAML-based integration style, left untouched pending user
> confirmation it's still needed. Follow CLAUDE.md's working principles
> (surgical changes, ask before assuming on hardware/threshold specifics,
> **ask before committing anything** — this was an explicit instruction
> this session and should carry forward unless the user says otherwise) and
> update RESUME.md before finishing.
