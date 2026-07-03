# CLAUDE.md

Guidance for AI agents (Claude Code or similar) working in this repository.

## Project summary

Solar heat collector automation for a Raspberry Pi. Reads roof-collector and tank
temperatures from PTC1000 sensors via an ADCDACPi board, drives a Shelly 1 relay
(the collector pump) over MQTT using hysteresis on the temperature differential,
and reports temperatures / estimated power production to Home Assistant. See
`README.md` for the full structure and data flow before making changes.

## Repository map (read README.md for detail)

- `src/main/HeatCollectorMain.py` — entry point, main sampling/control loop.
- `src/SensorManagement/ADCHandler.py` — ADCDACPi board wrapper.
- `src/TemperatureSensing/` — voltage→temperature conversion, circular-buffer filtering,
  plausibility checking (currently an empty stub).
- `src/RelayHandling/RelayHandling.py` — relay hysteresis logic over MQTT.
- `src/AuxiliaryFeatures/` — power estimation, calibration offset read/write.
- `HAConfigurationYAML/`, `HATemplates/` — Home Assistant integration config.
- `Design/` — Enterprise Architect model files (binary, don't attempt to edit as text).
- `ADCDACPi_Python_test/` — vendor demo script, not part of the production control flow.

## Hardware dependency: ADCDACPi library

`ADCHandler.py` and `HeatCollectorMain.py` import `ADCDACPi`, which is not on PyPI.
It must be installed from the AB Electronics UK library on the target Raspberry Pi
(see README.md "Dependencies" for exact install steps):
https://github.com/abelectronicsuk/ABElectronics_Python_Libraries
Do not assume `pip install ADCDACPi` works — it doesn't. If a task involves running
or testing the ADC read path, check this dependency is present first rather than
treating an ImportError as a code bug.

This is a small, single-purpose embedded-control codebase (no test suite, no build
system, no package manager beyond Python's own imports). It runs unattended on a
Raspberry Pi controlling physical hardware (relay/pump) — treat control-logic changes
(especially in `RelayHandling.py` and the main loop's thresholds) with real caution:
a bug here can run a pump needlessly or fail to protect the collector from overheating.

## Working principles

### 1. Think before coding
Don't assume. State assumptions explicitly; if genuinely uncertain about intent
(e.g. a threshold value, a hardware wiring detail, an MQTT topic name), ask rather
than guess. If multiple valid interpretations exist, say so instead of silently
picking one. If a simpler approach exists, say so.

### 2. Simplicity first
Minimum code that solves the problem. No speculative abstractions, no unrequested
configurability, no error handling for scenarios that can't occur on this hardware/
control path. This codebase favors small, direct scripts over frameworks — keep it
that way.

### 3. Surgical changes
Touch only what the task requires. Don't reformat or "improve" adjacent code. Match
existing style (this repo mixes tabs/spaces and inconsistent naming in places —
don't take that as license to refactor unless asked). Remove imports/variables that
your own change orphaned; leave pre-existing dead code alone (e.g. the empty
`MeasurementDataPlausibilityChecker.py` stub) unless the task is specifically about it.

### 4. Goal-driven execution
Turn vague asks into verifiable steps. Since there's no test suite, "verify" usually
means: read the changed code path end-to-end and confirm the logic is sound, or (if
asked) run the affected module directly with a small script to sanity-check
conversions/calculations (e.g. `VoltageToTempConverter`, `EnergyProductionCalculation`
are pure functions and easy to exercise standalone). For multi-step tasks, state a
brief plan before implementing.

## RESUME.md — required for every session

This repo uses a `RESUME.md` file at the repo root to carry context across sessions
with empty context windows. **Every agent session that makes a nontrivial change must
update `RESUME.md` before finishing.** It must contain:

1. **Most recent change** — what was changed, in which files, and why (1 short paragraph
   or bullet list, not a full diff).
2. **Current state** — anything in progress, known issues introduced or discovered,
   anything intentionally left undone.
3. **Continuation prompt** — a ready-to-paste block the user can copy into a fresh
   session's prompt so the next agent can pick up exactly where this one left off,
   without needing the prior conversation. Write it in second person, addressed to
   the next agent, and make it self-contained (don't say "as discussed" — say what
   was decided).

Keep `RESUME.md` short and current — overwrite stale sections rather than appending
a growing log. Git history already preserves the past; `RESUME.md` should describe
only *now* and *next*.
