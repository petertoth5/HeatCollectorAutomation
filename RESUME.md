# RESUME.md

## Most recent change

Fix wave on `feature/mqtt-reference-offset-correction` following the final
whole-branch code review of the MQTT reference-temperature offset correction
feature (topics `tempRoofReference`/`tempTankReference`, handlers
`on_roof_reference_message`/`on_tank_reference_message` in
`src/main/HeatCollectorMain.py`, calling
`OffsetCalculationAndStorage.compute_corrected_offset()`). All five approved
review findings fixed:

1. **Critical: uninitialized-average poisoning.** `RoofTemp`/`TankTemp`
   changed from initial value `0` to `None` (0 °C is a legitimate real
   reading, so it can't double as a sentinel). Both reference handlers now
   guard on `RoofTemp is None` / `TankTemp is None` and ignore the message
   (logged, not fatal) if the first real average hasn't been computed yet —
   protects against a retained-message-on-subscribe race that would
   otherwise compute `old_offset + (reference_temp - 0)` and persist a wildly
   wrong offset to disk.
2. **Rate limiting.** Added `RoofLastCorrectionTime`/`TankLastCorrectionTime`
   globals (`time.monotonic()`, initialized `None`) and a 30-second minimum
   spacing between accepted corrections per sensor (matches the ~30s the
   200-sample circular buffer takes to converge at the ~7 samples/sec
   sampling rate). Constant: `MIN_REFERENCE_CORRECTION_INTERVAL_SECONDS = 30`.
3. **Plausibility bound.** Reference payloads outside -20 to 120 °C are now
   rejected and logged, right after the existing `math.isfinite()` check.
4. **Correction logging.** Each handler now prints the reference value,
   current average, and resulting new offset immediately before persisting.
5. **README.md** "Automatic offset correction from reference sensors"
   section extended with a short paragraph documenting all three guards
   (average-not-ready, 30s rate limit, -20..120 °C plausibility bound).

Final guard order in both handlers (identical, verified by reading the code):
parse → `math.isfinite()` → range check (-20..120) → average-is-`None` check
→ 30s rate-limit check → compute + apply + log + `write_value()` persist.

`OffsetCalculationAndStorage.compute_corrected_offset()` itself was **not**
modified — confirmed via a standalone (uncommitted, deleted after use)
sanity script that it still produces the same results as before this fix
wave.

Full report: `.superpowers/sdd/2026-07-28-mqtt-reference-offset-correction/final-fix-report.md`.
Design/plan history: `docs/superpowers/specs/2026-07-28-mqtt-reference-offset-correction-design.md`,
`docs/superpowers/plans/2026-07-28-mqtt-reference-offset-correction.md`.

## Current state

- Branch `feature/mqtt-reference-offset-correction` has the feature plus this
  fix wave committed (6 commits ahead of `main`, ending at `1b96759`). Not
  yet merged to `main`, not yet verified on target hardware (all fixes so
  far verified only via static parse check + code tracing — no MQTT broker
  / Pi available in this environment).
- **Push blocked in this environment:** `git push -u origin
  feature/mqtt-reference-offset-correction` fails with `Permission denied
  (publickey)` — this sandbox has no SSH key for
  `git@github.com:petertoth5/HeatCollectorAutomation.git` (same failure
  seen on a plain `git pull` earlier in the session). The branch is fully
  committed and ready; **the user needs to push it themselves** and open
  the PR against `main` (`git push -u origin
  feature/mqtt-reference-offset-correction`, then create the PR).
- Separate, independent branch `fix/on-connect-rc-check` (single commit
  `d57b4e6`, forked from `main` before the reference-offset work started)
  also exists locally, also unpushed. It adds the same `rc != 0` early-return
  guard in `on_connect` that later got bundled into
  `feature/mqtt-reference-offset-correction`'s commit `226a917` (the
  reference-offset task brief assumed the guard already existed on `main`;
  it didn't, so the implementer added it again there, disclosed and
  reviewed as harmless). Net effect: whichever of these two branches merges
  to `main` second will produce a no-op/identical diff for that guard — not
  a conflict, just redundant history. Simplest resolution: after
  `feature/mqtt-reference-offset-correction` is merged, delete
  `fix/on-connect-rc-check` (its content is already included); alternatively
  merge/push `fix/on-connect-rc-check` first if the user wants the rc-check
  landed on `main` sooner on its own.
- No known regressions. No plausibility/rate-limit/None-guard bugs
  outstanding from the review that prompted this fix wave.
- Still open (unchanged from before this session): on-target manual
  verification of the whole reference-correction feature (publish via
  `mosquitto_pub` to `tempRoofReference`/`tempTankReference`, confirm
  `RoofOffset.txt`/`TankOffset.txt` update and the None/rate-limit/range
  guards behave as expected against the real sampling loop timing).
- Pre-existing open items (unchanged, not addressed by this work):
  `MeasurementDataPlausibilityChecker.py` is still an empty stub;
  `HATemplates/Sensor value difference.yaml` still has garbled quote
  characters; stale branches `improve_code_quality` and
  `fix/issue-4-global-state` still exist; `main` still has no branch
  protection ruleset; no automated test suite.

## Continuation prompt

Paste this into a new session to continue:

> Read README.md and CLAUDE.md. Branch `feature/mqtt-reference-offset-correction`
> has the MQTT reference-temperature offset correction feature implemented
> and a follow-up fix wave applied (uninitialized-average `None` guards,
> 30s per-sensor rate limiting, -20..120 °C plausibility bound on the
> reference value, correction logging, README updates — see
> `.superpowers/sdd/2026-07-28-mqtt-reference-offset-correction/final-fix-report.md`
> for the full report and commit hash(es)). All changes are verified so far
> only via static parse check and manual code tracing — there is no MQTT
> broker or Raspberry Pi in this environment. The branch is fully committed
> (ends at `1b96759`) but could NOT be pushed from this environment — `git
> push` fails with `Permission denied (publickey)` (no SSH key here for
> `git@github.com:petertoth5/HeatCollectorAutomation.git`). The user needs
> to push it themselves and open the PR. There's also a separate unpushed
> branch `fix/on-connect-rc-check` (commit `d57b4e6`, forked from `main`
> before this feature) whose single `on_connect` rc-check fix got
> independently bundled into this feature branch's commit `226a917` too —
> once `feature/mqtt-reference-offset-correction` merges, `fix/on-connect-
> rc-check` is redundant and can be deleted. Next step after the user has
> pushed and merged: on-target manual verification (publish test payloads
> via `mosquitto_pub -h <broker> -t tempRoofReference -m "<value>"` and the
> tank equivalent) once the user has access to the real hardware.
> Pre-existing open items, unchanged: `MeasurementDataPlausibilityChecker.py`
> is still an empty stub; `HATemplates/Sensor value difference.yaml` still
> has garbled quote characters; stale branches `improve_code_quality` and
> `fix/issue-4-global-state` still exist; `main` has no branch protection
> ruleset; no automated test suite exists (verification is via standalone
> scripts, not pytest). Follow CLAUDE.md's working principles (surgical
> changes, ask before assuming on hardware/threshold specifics) and update
> RESUME.md before finishing.
