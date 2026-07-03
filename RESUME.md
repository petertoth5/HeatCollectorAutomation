# RESUME.md

## Most recent change

Added repo documentation:
- Rewrote `README.md` with full repo structure, data flow, hardware/integration points,
  and known gaps.
- Added `CLAUDE.md` with repo-specific agent guidance (working principles adapted from
  Karpathy-style CLAUDE.md guidelines: think before coding, simplicity first, surgical
  changes, goal-driven execution) plus the requirement to maintain this `RESUME.md` file.
- Created this `RESUME.md` file per the new process.

No production code (`src/**`) was changed in this session — documentation only.

## Current state

- Codebase has no automated tests.
- `src/TemperatureSensing/MeasurementDataPlausibilityChecker.py` is still an empty stub;
  the `errorFlagRoof`/`errorFlagTank` flags in `HeatCollectorMain.py` are set on bad
  readings but never used to suppress publishing or halt relay control — known gap,
  not addressed.
- `HATemplates/Sensor value difference.yaml` contains mangled/garbled quote characters
  (looks like an encoding issue, not valid YAML as-is) — not fixed, flagged only.

## Continuation prompt

Paste this into a new session to continue:

> Read README.md and CLAUDE.md in this repo first. Last session added baseline
> documentation (README.md, CLAUDE.md, RESUME.md) but made no code changes. Known
> open items: (1) `MeasurementDataPlausibilityChecker.py` is an empty stub while
> `errorFlagRoof`/`errorFlagTank` in `HeatCollectorMain.py` are computed but unused —
> decide whether to implement plausibility checking or remove the dead flags; (2)
> `HATemplates/Sensor value difference.yaml` has garbled quote characters, likely an
> encoding artifact — check and fix if it's meant to be valid YAML. No test suite
> exists. Follow the working principles in CLAUDE.md (surgical changes, ask before
> assuming on hardware/threshold specifics) and update RESUME.md before finishing.
