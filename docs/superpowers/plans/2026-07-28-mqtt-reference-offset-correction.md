# MQTT Reference-Temperature Offset Correction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the Pi auto-correct `RoofOffset`/`TankOffset` when reference roof/tank temperatures arrive from an external sensor over MQTT, so the Pi's own PTC1000 readings track the reference.

**Architecture:** Two new MQTT topics (`tempRoofReference`, `tempTankReference`) each get a `message_callback_add` handler in `HeatCollectorMain.py`, mirroring the existing manual-offset handlers. Each handler validates the payload, calls a new pure function `compute_corrected_offset()` (added to `OffsetCalculationAndStorage.py`, the module that already owns offset read/write) to get the new offset, updates the in-memory global, and persists it to the existing `.txt` file via the existing `write_value()`.

**Tech Stack:** Python 3, paho-mqtt (VERSION1 API, already in use), no test framework (repo has none — verification is via standalone `python -c` sanity checks, per this repo's `CLAUDE.md`).

## Global Constraints

- No automated test suite in this repo — every "test" step below is a standalone script run with `python`, not pytest.
- Match existing code style in `HeatCollectorMain.py`: tab-indented function bodies (not spaces), same log-message phrasing style as existing handlers.
- No plausibility/range bounds on reference values beyond `math.isfinite()` — matches the approved spec.
- Don't touch the main sampling loop, relay logic, or the existing manual offset topics.

---

### Task 1: Pure offset-correction formula in `OffsetCalculationAndStorage.py`

**Files:**
- Modify: `src/AuxiliaryFeatures/OffsetCalculationAndStorage.py`

**Interfaces:**
- Produces: `compute_corrected_offset(reference_temp: float, current_avg_temp: float, old_offset: float) -> float` — used by Task 2's two MQTT handlers.

- [ ] **Step 1: Write the standalone sanity script**

Create a scratch file (not committed) to exercise the formula before writing it, so you can see it fail first:

```python
# scratch_test_offset_formula.py
import sys
sys.path.insert(0, "src")
from AuxiliaryFeatures.OffsetCalculationAndStorage import compute_corrected_offset

# Buffer avg is 22.0 (raw + old offset of 1.0), reference says true temp is 24.0.
# raw = 22.0 - 1.0 = 21.0; new_offset should be 24.0 - 21.0 = 3.0
result = compute_corrected_offset(reference_temp=24.0, current_avg_temp=22.0, old_offset=1.0)
assert result == 3.0, f"expected 3.0, got {result}"

# No drift case: reference matches current avg exactly -> offset unchanged.
result2 = compute_corrected_offset(reference_temp=22.0, current_avg_temp=22.0, old_offset=1.0)
assert result2 == 1.0, f"expected 1.0, got {result2}"

print("OK")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python scratch_test_offset_formula.py`
Expected: `ImportError: cannot import name 'compute_corrected_offset'`

- [ ] **Step 3: Implement the function**

Add to `src/AuxiliaryFeatures/OffsetCalculationAndStorage.py` (append after `write_value`):

```python
def compute_corrected_offset(reference_temp, current_avg_temp, old_offset):
    return old_offset + (reference_temp - current_avg_temp)
```

- [ ] **Step 4: Run the sanity script to verify it passes**

Run: `python scratch_test_offset_formula.py`
Expected: `OK`

Delete the scratch script afterward — it's not part of the repo (no test suite exists to house it in).

- [ ] **Step 5: Commit**

```bash
git add src/AuxiliaryFeatures/OffsetCalculationAndStorage.py
git commit -m "Add compute_corrected_offset formula for reference-temp correction"
```

---

### Task 2: MQTT reference-temperature topics and handlers

**Files:**
- Modify: `src/main/HeatCollectorMain.py`

**Interfaces:**
- Consumes: `OffsetCalculationAndStorage.compute_corrected_offset(reference_temp, current_avg_temp, old_offset) -> float` (Task 1).
- Consumes existing: `OffsetCalculationAndStorage.write_value(value, file_path)`, existing globals `RoofOffset`, `TankOffset`, `RoofTemp`, `TankTemp`.

- [ ] **Step 1: Add topic constants**

In `src/main/HeatCollectorMain.py`, right after the existing offset topic constants (line 42, after `MQTT_TANKOFFSET_TOPIC = "tempTankOffsetByUser"`), add:

```python
MQTT_ROOFREFERENCE_TOPIC = "tempRoofReference"
MQTT_TANKREFERENCE_TOPIC = "tempTankReference"
```

- [ ] **Step 2: Subscribe both topics in `on_connect`**

Modify `on_connect` (currently lines 61-64) to also subscribe the new topics, keeping the existing `rc` check from the prior fix:

```python
def on_connect(mosq, obj, flags, rc):
	if rc != 0:
		print(f"Error: MQTT connection failed with rc={rc}, not subscribing.")
		return
	print ("Connected to MQTT Broker")
	mosq.subscribe(MQTT_ROOFOFFSET_TOPIC)
	mosq.subscribe(MQTT_TANKOFFSET_TOPIC)
	mosq.subscribe(MQTT_ROOFREFERENCE_TOPIC)
	mosq.subscribe(MQTT_TANKREFERENCE_TOPIC)
```

- [ ] **Step 3: Add the two reference-message handlers**

Add after the existing `on_tank_offset_message` (currently ends at line 96), before `def power_calc_job`:

```python
# Define on_message handler for reference roof temperature corrections
def on_roof_reference_message(client, userdata, msg):
	global RoofOffset
	try:
		reference_temp = float(msg.payload.decode().strip())
	except ValueError:
		print("Error: received roof reference payload is not a valid number.")
		return
	if not math.isfinite(reference_temp):
		print("Error: received roof reference payload is not a finite number.")
		return
	RoofOffset = OffsetCalculationAndStorage.compute_corrected_offset(reference_temp, RoofTemp, RoofOffset)
	OffsetCalculationAndStorage.write_value(RoofOffset, ROOF_OFFSET_FILE)

# Define on_message handler for reference tank temperature corrections
def on_tank_reference_message(client, userdata, msg):
	global TankOffset
	try:
		reference_temp = float(msg.payload.decode().strip())
	except ValueError:
		print("Error: received tank reference payload is not a valid number.")
		return
	if not math.isfinite(reference_temp):
		print("Error: received tank reference payload is not a finite number.")
		return
	TankOffset = OffsetCalculationAndStorage.compute_corrected_offset(reference_temp, TankTemp, TankOffset)
	OffsetCalculationAndStorage.write_value(TankOffset, TANK_OFFSET_FILE)
```

- [ ] **Step 4: Register the new callbacks in `main()`**

In `main()`, modify the existing block (currently lines 154-155):

```python
    mqttc.message_callback_add(MQTT_ROOFOFFSET_TOPIC, on_roof_offset_message)
    mqttc.message_callback_add(MQTT_TANKOFFSET_TOPIC, on_tank_offset_message)
```

to add two more lines directly below:

```python
    mqttc.message_callback_add(MQTT_ROOFOFFSET_TOPIC, on_roof_offset_message)
    mqttc.message_callback_add(MQTT_TANKOFFSET_TOPIC, on_tank_offset_message)
    mqttc.message_callback_add(MQTT_ROOFREFERENCE_TOPIC, on_roof_reference_message)
    mqttc.message_callback_add(MQTT_TANKREFERENCE_TOPIC, on_tank_reference_message)
```

- [ ] **Step 5: Static sanity check (no MQTT broker needed)**

Run: `python -c "import sys; sys.path.insert(0, 'src'); sys.path.insert(0, '.'); import ast; ast.parse(open('src/main/HeatCollectorMain.py').read())"`
Expected: no output, exit code 0 (confirms the file still parses as valid Python after the edits — this repo has no import-safe way to load the module directly since it imports the hardware-only `ADCDACPi` package at module scope).

- [ ] **Step 6: On-target manual verification (requires the real Pi + broker + running service)**

Not runnable in a dev sandbox — record as a manual follow-up:

```bash
mosquitto_pub -h <MQTT_BROKER> -t tempRoofReference -m "24.3"
mosquitto_pub -h <MQTT_BROKER> -t tempTankReference -m "41.8"
```

Expected: `RoofOffset.txt`/`TankOffset.txt` update to the computed values; the console/MQTT-published `RoofTemp`/`TankTemp` converge toward `24.3`/`41.8` over the next few sample cycles; no crash on an invalid payload (e.g. `mosquitto_pub ... -m "abc"` logs an error and leaves the offset unchanged).

- [ ] **Step 7: Commit**

```bash
git add src/main/HeatCollectorMain.py
git commit -m "Add MQTT reference-temperature topics for automatic offset correction"
```

---

### Task 3: Document the feature in `README.md`

**Files:**
- Modify: `README.md`

**Interfaces:**
- None (documentation only).

- [ ] **Step 1: Add a new section after "Adjusting sensor calibration offsets via MQTT"**

Insert after the existing offset section (after the paragraph ending "...nothing crashes.", before "## Running as a systemd service"):

```markdown
## Automatic offset correction from reference sensors

If independent reference roof/tank sensors are available, publish their
readings to these topics and the Pi will recompute its own calibration
offset to match, immediately and on every message:

| Topic | Adjusts | Example payload |
|-------|---------|------------------|
| `tempRoofReference` | `RoofOffset.txt` / roof sensor | `24.3` |
| `tempTankReference` | `TankOffset.txt` / tank sensor | `41.8` |

```
mosquitto_pub -h <MQTT_BROKER> -t tempRoofReference -m "24.3"
mosquitto_pub -h <MQTT_BROKER> -t tempTankReference -m "41.8"
```

Unlike the manual `...OffsetByUser` topics (which set the offset directly),
these topics carry the *true* temperature; the new offset is derived as
`old_offset + (reference_temp - current_averaged_temp)`, so the Pi's
reported temperature converges to the reference value rather than being
overwritten by it. Same payload validation as the manual offset topics: a
non-finite or unparseable payload is logged and ignored.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "Document MQTT reference-temperature offset correction"
```

---

## Self-Review Notes

- Spec coverage: topics (Task 2 Step 1), formula (Task 1), handler validation (Task 2 Step 3), persistence (Task 2 Step 3), on_connect subscription (Task 2 Step 2), documentation (Task 3) — all covered. No task needed for "interaction with manual offset feature" since the spec states no special coordination is implemented (both simply write the same global/file).
- Placeholder scan: none found.
- Type consistency: `compute_corrected_offset(reference_temp, current_avg_temp, old_offset)` signature is identical between Task 1's definition and Task 2's two call sites.
