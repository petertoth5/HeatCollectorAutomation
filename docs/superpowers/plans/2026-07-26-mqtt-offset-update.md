# MQTT Offset Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a user push new roof/tank calibration offsets over MQTT at runtime; the running process applies the new value immediately and persists it to the existing offset text file.

**Architecture:** Two new MQTT subscriptions (`tempRoofOffsetByUser`, `tempTankOffsetByUser`), each with its own `message_callback_add` handler in `HeatCollectorMain.py`. A handler parses the payload as a float, updates the module-level global offset, and calls the existing `OffsetCalculationAndStorage.write_value()` to persist it. `mqttc.loop_start()` is added so subscribed messages are actually delivered (nothing runs paho's network loop today).

**Tech Stack:** Python 3, `paho-mqtt` 2.0 (already a dependency), stdlib only otherwise.

## Global Constraints

- No test framework (pytest etc.) is installed or used in this repo — verification uses small standalone scripts run with plain `python`, not a test runner. Do not add pytest or any new dependency.
- `HeatCollectorMain.py` cannot be imported in this dev environment without stubbing the `ADCDACPi` import first — `ADCDACPi` itself is installed but its underlying `spidev` (Raspberry Pi SPI hardware library) is not, and never will be off-Pi. Every verification step that imports `HeatCollectorMain` must stub `sys.modules['ADCDACPi']` before the import. This is a workaround for verification only — do not change how `HeatCollectorMain.py` itself imports `ADCDACPi`.
- Accepted offset payload format is a plain numeric string (e.g. `"2.5"`), matching the existing `RoofOffset.txt`/`TankOffset.txt` file format. No JSON, no bounds/validation beyond "is it a valid float".
- On an invalid payload: print an error and leave the in-memory offset and the file untouched. Never raise/crash — this is an unattended process controlling a physical pump relay.
- Verification scripts must be run with cwd = `src/main` (matches how `HeatCollectorMain.py` is normally run; its own `sys.path.append('../')` and the relative `RoofOffset.txt`/`TankOffset.txt` reads assume this).
- Surgical changes only — don't reformat or restructure unrelated code in `HeatCollectorMain.py`.

---

### Task 1: Add topic/file-path constants and replace inline literals

**Files:**
- Modify: `src/main/HeatCollectorMain.py:34-53`

**Interfaces:**
- Produces: module-level constants `MQTT_ROOFOFFSET_TOPIC`, `MQTT_TANKOFFSET_TOPIC`, `ROOF_OFFSET_FILE`, `TANK_OFFSET_FILE` — consumed by Task 2 and Task 3.

- [ ] **Step 1: Add the four new constants**

In `src/main/HeatCollectorMain.py`, current lines 34-41:

```python
MQTT_BROKER = "192.168.1.100"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL = 45
MQTT_ROOFTEMP_TOPIC = "TemperatureRoof"
MQTT_TANKTEMP_TOPIC = "TemperatureTank"
MQTT_SUNCOLLECTOR_POWER_TOPIC = "SunCollectorPower"
WATER_VOLUME = 30
INTEGRATION_TIME_SECONDS = 300
```

Replace with:

```python
MQTT_BROKER = "192.168.1.100"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL = 45
MQTT_ROOFTEMP_TOPIC = "TemperatureRoof"
MQTT_TANKTEMP_TOPIC = "TemperatureTank"
MQTT_SUNCOLLECTOR_POWER_TOPIC = "SunCollectorPower"
MQTT_ROOFOFFSET_TOPIC = "tempRoofOffsetByUser"
MQTT_TANKOFFSET_TOPIC = "tempTankOffsetByUser"
ROOF_OFFSET_FILE = "RoofOffset.txt"
TANK_OFFSET_FILE = "TankOffset.txt"
WATER_VOLUME = 30
INTEGRATION_TIME_SECONDS = 300
```

- [ ] **Step 2: Use the new file-path constants at startup**

Current lines 52-53:

```python
TankOffset = OffsetCalculationAndStorage.read_and_convert("TankOffset.txt")
RoofOffset = OffsetCalculationAndStorage.read_and_convert("RoofOffset.txt")
```

Replace with:

```python
TankOffset = OffsetCalculationAndStorage.read_and_convert(TANK_OFFSET_FILE)
RoofOffset = OffsetCalculationAndStorage.read_and_convert(ROOF_OFFSET_FILE)
```

- [ ] **Step 3: Syntax-check the file**

Run: `python -m py_compile src/main/HeatCollectorMain.py`
Expected: no output, exit code 0.

- [ ] **Step 4: Commit**

```bash
git add src/main/HeatCollectorMain.py
git commit -m "Add MQTT offset topic and file-path constants"
```

---

### Task 2: Implement the offset-message handlers

**Files:**
- Modify: `src/main/HeatCollectorMain.py:55-61` (add handlers after existing `on_connect`/`on_publish`)
- Test: `C:\Users\peter\AppData\Local\Temp\claude\c--Projects-GitWorkspace-HeatCollectorAutomation\6210b030-bc34-44c4-90b1-d0dd1ceca5ce\scratchpad\verify_offset_handlers.py` (scratch verification script, not committed)

**Interfaces:**
- Consumes: `MQTT_ROOFOFFSET_TOPIC`, `MQTT_TANKOFFSET_TOPIC`, `ROOF_OFFSET_FILE`, `TANK_OFFSET_FILE` (Task 1); `OffsetCalculationAndStorage.write_value(tempOffset, file_path)` (existing); globals `RoofOffset`, `TankOffset` (existing, `src/main/HeatCollectorMain.py:49-53`).
- Produces: `on_roof_offset_message(client, userdata, msg)`, `on_tank_offset_message(client, userdata, msg)` — consumed by Task 3's `message_callback_add` calls.

- [ ] **Step 1: Add the two handler functions**

In `src/main/HeatCollectorMain.py`, current lines 59-61:

```python
# Define on_publish event Handler
def on_publish(client, userdata, mid):
	print ("Message Published...")
```

Replace with (adds two new functions right after `on_publish`):

```python
# Define on_publish event Handler
def on_publish(client, userdata, mid):
	print ("Message Published...")

# Define on_message handler for user-supplied roof offset updates
def on_roof_offset_message(client, userdata, msg):
	global RoofOffset
	try:
		new_offset = float(msg.payload.decode().strip())
	except ValueError:
		print("Error: received roof offset payload is not a valid number.")
		return
	RoofOffset = new_offset
	OffsetCalculationAndStorage.write_value(RoofOffset, ROOF_OFFSET_FILE)

# Define on_message handler for user-supplied tank offset updates
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

(Match the existing file's tab indentation for function bodies, as shown above.)

- [ ] **Step 2: Write the standalone verification script**

Create `verify_offset_handlers.py` in the scratchpad directory:

```python
import sys
import types
import shutil
from pathlib import Path
from types import SimpleNamespace

# Stub ADCDACPi: its real import chain requires spidev, a Raspberry Pi-only
# SPI library that will never be installed in this dev environment.
fake_adcdacpi_pkg = types.ModuleType("ADCDACPi")
fake_adcdacpi_pkg.ADCDACPi = object
sys.modules["ADCDACPi"] = fake_adcdacpi_pkg

REPO_ROOT = Path(r"c:\Projects\GitWorkspace\HeatCollectorAutomation")
MAIN_DIR = REPO_ROOT / "src" / "main"

# Back up the real offset files, restore at the end no matter what.
roof_file = MAIN_DIR / "RoofOffset.txt"
tank_file = MAIN_DIR / "TankOffset.txt"
roof_backup = roof_file.read_text()
tank_backup = tank_file.read_text()

import os
os.chdir(MAIN_DIR)
sys.path.insert(0, str(MAIN_DIR))

try:
    import HeatCollectorMain as hcm

    # --- valid roof payload updates global + file ---
    hcm.on_roof_offset_message(None, None, SimpleNamespace(payload=b"3.5", topic=hcm.MQTT_ROOFOFFSET_TOPIC))
    assert hcm.RoofOffset == 3.5, f"expected RoofOffset == 3.5, got {hcm.RoofOffset}"
    assert roof_file.read_text().strip() == "3.5", f"expected file '3.5', got {roof_file.read_text()!r}"
    print("PASS: valid roof payload updates global and file")

    # --- valid tank payload updates global + file ---
    hcm.on_tank_offset_message(None, None, SimpleNamespace(payload=b"-1.25", topic=hcm.MQTT_TANKOFFSET_TOPIC))
    assert hcm.TankOffset == -1.25, f"expected TankOffset == -1.25, got {hcm.TankOffset}"
    assert tank_file.read_text().strip() == "-1.25", f"expected file '-1.25', got {tank_file.read_text()!r}"
    print("PASS: valid tank payload updates global and file")

    # --- invalid payload leaves global and file untouched ---
    offset_before = hcm.RoofOffset
    file_before = roof_file.read_text()
    hcm.on_roof_offset_message(None, None, SimpleNamespace(payload=b"not-a-number", topic=hcm.MQTT_ROOFOFFSET_TOPIC))
    assert hcm.RoofOffset == offset_before, f"expected RoofOffset unchanged at {offset_before}, got {hcm.RoofOffset}"
    assert roof_file.read_text() == file_before, "expected file unchanged on invalid payload"
    print("PASS: invalid payload leaves global and file untouched")

finally:
    roof_file.write_text(roof_backup)
    tank_file.write_text(tank_backup)
```

- [ ] **Step 3: Run the verification script and confirm it fails before the handlers exist**

(Skip this only if Step 1 above is already applied — run this step first if doing strict TDD by temporarily commenting out the two new functions.)

Run: `python "C:\Users\peter\AppData\Local\Temp\claude\c--Projects-GitWorkspace-HeatCollectorAutomation\6210b030-bc34-44c4-90b1-d0dd1ceca5ce\scratchpad\verify_offset_handlers.py"`
Expected (if handlers not yet added): `AttributeError: module 'HeatCollectorMain' has no attribute 'on_roof_offset_message'`

- [ ] **Step 4: Apply Step 1's handler code, then re-run the verification script**

Run: `python "C:\Users\peter\AppData\Local\Temp\claude\c--Projects-GitWorkspace-HeatCollectorAutomation\6210b030-bc34-44c4-90b1-d0dd1ceca5ce\scratchpad\verify_offset_handlers.py"`
Expected:
```
PASS: valid roof payload updates global and file
PASS: valid tank payload updates global and file
PASS: invalid payload leaves global and file untouched
```

- [ ] **Step 5: Confirm the real offset files are unchanged after the script ran**

Run: `git status --short`
Expected: no changes shown for `src/main/RoofOffset.txt` or `src/main/TankOffset.txt` (the script restores them in its `finally` block).

- [ ] **Step 6: Commit**

```bash
git add src/main/HeatCollectorMain.py
git commit -m "Add on_roof_offset_message/on_tank_offset_message handlers"
```

---

### Task 3: Wire subscriptions into main()

**Files:**
- Modify: `src/main/HeatCollectorMain.py:113-114` (right after `mqttc.connect(...)`)

**Interfaces:**
- Consumes: `MQTT_ROOFOFFSET_TOPIC`, `MQTT_TANKOFFSET_TOPIC` (Task 1); `on_roof_offset_message`, `on_tank_offset_message` (Task 2).
- Produces: running process now has a live paho network loop and active subscriptions — nothing downstream depends on this beyond end-to-end/hardware behavior.

- [ ] **Step 1: Add subscribe, message_callback_add, and loop_start calls**

Current lines 113-116:

```python
    # Connect with MQTT Broker
    mqttc.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE_INTERVAL) 

    schedule.every(INTEGRATION_TIME_SECONDS).seconds.do(power_calc_job, mqttc)
```

Replace with:

```python
    # Connect with MQTT Broker
    mqttc.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE_INTERVAL) 

    # Subscribe to user-supplied offset updates
    mqttc.subscribe(MQTT_ROOFOFFSET_TOPIC)
    mqttc.subscribe(MQTT_TANKOFFSET_TOPIC)
    mqttc.message_callback_add(MQTT_ROOFOFFSET_TOPIC, on_roof_offset_message)
    mqttc.message_callback_add(MQTT_TANKOFFSET_TOPIC, on_tank_offset_message)

    # Run paho's network loop in a background thread so subscribed
    # messages are delivered; publish() alone doesn't require this,
    # but subscribe callbacks never fire without it.
    mqttc.loop_start()

    schedule.every(INTEGRATION_TIME_SECONDS).seconds.do(power_calc_job, mqttc)
```

- [ ] **Step 2: Syntax-check the file**

Run: `python -m py_compile src/main/HeatCollectorMain.py`
Expected: no output, exit code 0.

- [ ] **Step 3: Manual code read-through**

Re-read `src/main/HeatCollectorMain.py:94-135` (the full `main()` setup section) end-to-end and confirm: constants from Task 1 are used consistently, both handlers from Task 2 are referenced by the exact same names, and `loop_start()` is called before the `while True` sampling loop begins. This substitutes for an integration test — full subscribe/publish behavior against a real broker cannot be verified in this dev environment (no ADCDACPi/spidev hardware, no target Pi) and is deferred to on-target testing per the spec's Testing section.

- [ ] **Step 4: Commit**

```bash
git add src/main/HeatCollectorMain.py
git commit -m "Subscribe to user offset topics and start MQTT network loop"
```

---

### Task 4: Update RESUME.md

**Files:**
- Modify: `RESUME.md`

- [ ] **Step 1: Rewrite RESUME.md's three required sections**

Replace the entire contents of `RESUME.md` with:

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add RESUME.md
git commit -m "Update RESUME.md for MQTT offset update feature"
```
