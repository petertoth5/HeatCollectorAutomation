# MQTT Offset State Publish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pi publishes its currently-applied `RoofOffset`/`TankOffset` to retained MQTT topics whenever they change (from any source), so the HA dashboard's offset `number` entities always reflect the real device state.

**Architecture:** Two new retained MQTT topics (`RoofOffsetCurrent`, `TankOffsetCurrent`). A publish call is added right after each of the four existing offset-change handlers' `write_value()` call (using the handler's own `client` parameter, which *is* the connected `mqttc` instance in a `message_callback_add` callback), plus one startup publish in `main()`. HA's existing `Roof Offset`/`Tank Offset` `number` entities gain a `state_topic` pointing at the new topics.

**Tech Stack:** Python 3, paho-mqtt (VERSION1 API, already in use), Home Assistant MQTT `number` platform. No test framework — verification is via `ast.parse` and manual on-target `mosquitto_sub`/HA checks, per this repo's `CLAUDE.md`.

## Global Constraints

- No automated test suite in this repo — every "test" step is a standalone script or `ast.parse` check, not pytest.
- Retain flag (`retain=True`) on both new topics — required per the approved spec, not optional.
- Topic names are exactly `RoofOffsetCurrent` and `TankOffsetCurrent` (PascalCase, matching `TemperatureRoof`/`TemperatureTank`/`SunCollectorPower` naming style — do not use camelCase or add a `temp` prefix, that's reserved for the incoming command/reference topics).
- Do not touch the manual/reference offset validation logic, the sampling loop, or relay logic — this is purely additive publish calls.
- Only the existing `Roof Offset`/`Tank Offset` HA `number` entities get a `state_topic`. The `Roof Reference Temperature`/`Tank Reference Temperature` entities added in the prior feature stay write-only — do not add a state_topic to those.

---

### Task 1: Publish current offset on every change and at startup

**Files:**
- Modify: `src/main/HeatCollectorMain.py`

**Interfaces:**
- No new functions. Uses existing `OffsetCalculationAndStorage.write_value` (unchanged) and each handler's own `client`/`mqttc` parameter.

- [ ] **Step 1: Add the two new topic constants**

In `src/main/HeatCollectorMain.py`, right after the existing reference-topic constants (currently lines 43-44, after `MQTT_TANKREFERENCE_TOPIC = "tempTankReference"`), add:

```python
MQTT_ROOFOFFSETCURRENT_TOPIC = "RoofOffsetCurrent"
MQTT_TANKOFFSETCURRENT_TOPIC = "TankOffsetCurrent"
```

- [ ] **Step 2: Publish after the manual roof offset write**

In `on_roof_offset_message` (currently lines 87-98), add a publish call right after the existing `write_value` line:

```python
# Define on_message handler for user-supplied roof offset updates
def on_roof_offset_message(client, userdata, msg):
	global RoofOffset
	try:
		new_offset = float(msg.payload.decode().strip())
	except ValueError:
		print("Error: received roof offset payload is not a valid number.")
		return
	if not math.isfinite(new_offset):
		print("Error: received roof offset payload is not a finite number.")
		return
	RoofOffset = new_offset
	OffsetCalculationAndStorage.write_value(RoofOffset, ROOF_OFFSET_FILE)
	client.publish(MQTT_ROOFOFFSETCURRENT_TOPIC, RoofOffset, retain=True)
```

- [ ] **Step 3: Publish after the manual tank offset write**

In `on_tank_offset_message` (currently lines 101-112), same pattern:

```python
# Define on_message handler for user-supplied tank offset updates
def on_tank_offset_message(client, userdata, msg):
	global TankOffset
	try:
		new_offset = float(msg.payload.decode().strip())
	except ValueError:
		print("Error: received tank offset payload is not a valid number.")
		return
	if not math.isfinite(new_offset):
		print("Error: received tank offset payload is not a finite number.")
		return
	TankOffset = new_offset
	OffsetCalculationAndStorage.write_value(TankOffset, TANK_OFFSET_FILE)
	client.publish(MQTT_TANKOFFSETCURRENT_TOPIC, TankOffset, retain=True)
```

- [ ] **Step 4: Publish after the roof reference-correction write**

In `on_roof_reference_message` (currently lines 115-137), add the publish call right after the existing `write_value` line (which is the last line of the function):

```python
# Define on_message handler for reference roof temperature corrections
def on_roof_reference_message(client, userdata, msg):
	global RoofOffset, RoofLastCorrectionTime
	try:
		reference_temp = float(msg.payload.decode().strip())
	except ValueError:
		print("Error: received roof reference payload is not a valid number.")
		return
	if not math.isfinite(reference_temp):
		print("Error: received roof reference payload is not a finite number.")
		return
	if reference_temp < -20 or reference_temp > 120:
		print("Error: received roof reference payload is outside plausible range (-20 to 120 C).")
		return
	if RoofTemp is None:
		print("Error: no roof temperature average yet, ignoring reference message.")
		return
	if RoofLastCorrectionTime is not None and (time.monotonic() - RoofLastCorrectionTime) < MIN_REFERENCE_CORRECTION_INTERVAL_SECONDS:
		print("Error: roof reference correction ignored, last correction was less than 30s ago.")
		return
	RoofOffset = OffsetCalculationAndStorage.compute_corrected_offset(reference_temp, RoofTemp, RoofOffset)
	RoofLastCorrectionTime = time.monotonic()
	print(f"Roof reference {reference_temp}, current avg {RoofTemp}, new offset {RoofOffset}")
	OffsetCalculationAndStorage.write_value(RoofOffset, ROOF_OFFSET_FILE)
	client.publish(MQTT_ROOFOFFSETCURRENT_TOPIC, RoofOffset, retain=True)
```

- [ ] **Step 5: Publish after the tank reference-correction write**

In `on_tank_reference_message` (currently lines 140-162), same pattern:

```python
# Define on_message handler for reference tank temperature corrections
def on_tank_reference_message(client, userdata, msg):
	global TankOffset, TankLastCorrectionTime
	try:
		reference_temp = float(msg.payload.decode().strip())
	except ValueError:
		print("Error: received tank reference payload is not a valid number.")
		return
	if not math.isfinite(reference_temp):
		print("Error: received tank reference payload is not a finite number.")
		return
	if reference_temp < -20 or reference_temp > 120:
		print("Error: received tank reference payload is outside plausible range (-20 to 120 C).")
		return
	if TankTemp is None:
		print("Error: no tank temperature average yet, ignoring reference message.")
		return
	if TankLastCorrectionTime is not None and (time.monotonic() - TankLastCorrectionTime) < MIN_REFERENCE_CORRECTION_INTERVAL_SECONDS:
		print("Error: tank reference correction ignored, last correction was less than 30s ago.")
		return
	TankOffset = OffsetCalculationAndStorage.compute_corrected_offset(reference_temp, TankTemp, TankOffset)
	TankLastCorrectionTime = time.monotonic()
	print(f"Tank reference {reference_temp}, current avg {TankTemp}, new offset {TankOffset}")
	OffsetCalculationAndStorage.write_value(TankOffset, TANK_OFFSET_FILE)
	client.publish(MQTT_TANKOFFSETCURRENT_TOPIC, TankOffset, retain=True)
```

- [ ] **Step 6: Publish once at startup**

In `main()`, right after `mqttc.loop_start()` (currently line 228) and before `schedule.every(...)` (currently line 230), add:

```python
    # Publish the offsets read from disk at startup, retained, so a
    # freshly (re)subscribed HA dashboard sees the real value immediately
    # rather than waiting for the next offset change on the Pi.
    mqttc.publish(MQTT_ROOFOFFSETCURRENT_TOPIC, RoofOffset, retain=True)
    mqttc.publish(MQTT_TANKOFFSETCURRENT_TOPIC, TankOffset, retain=True)
```

- [ ] **Step 7: Static sanity check**

Run: `python -c "import ast; ast.parse(open('src/main/HeatCollectorMain.py').read())"`
Expected: no output, exit code 0.

- [ ] **Step 8: Commit**

```bash
git add src/main/HeatCollectorMain.py
git commit -m "Publish currently-applied offsets to MQTT on every change and at startup"
```

---

### Task 2: HA dashboard state_topic and README documentation

**Files:**
- Modify: `HAConfigurationYAML/configuration.yaml`
- Modify: `README.md`

**Interfaces:**
- None (configuration/documentation only). Consumes the topic names `RoofOffsetCurrent`/`TankOffsetCurrent` published by Task 1.

- [ ] **Step 1: Add state_topic to the existing Roof Offset / Tank Offset number entities**

In `HAConfigurationYAML/configuration.yaml`, the current `number:` block (under `mqtt:`) reads:

```yaml
  number:
    - name: "Roof Offset"
      command_topic: "tempRoofOffsetByUser"
      min: -100
      max: 100
      step: 0.1
      mode: box
    - name: "Tank Offset"
      command_topic: "tempTankOffsetByUser"
      min: -100
      max: 100
      step: 0.1
      mode: box
    - name: "Roof Reference Temperature"
      unique_id: "RoofReferenceTemperature_001"
      command_topic: "tempRoofReference"
      min: -20
      max: 120
      step: 0.1
      mode: box
    - name: "Tank Reference Temperature"
      unique_id: "TankReferenceTemperature_001"
      command_topic: "tempTankReference"
      min: -20
      max: 120
      step: 0.1
      mode: box
```

Change only the first two entries (`Roof Offset`, `Tank Offset`) to add a `state_topic` line each, right after their `command_topic` line. Do not touch the two Reference Temperature entries:

```yaml
  number:
    - name: "Roof Offset"
      command_topic: "tempRoofOffsetByUser"
      state_topic: "RoofOffsetCurrent"
      min: -100
      max: 100
      step: 0.1
      mode: box
    - name: "Tank Offset"
      command_topic: "tempTankOffsetByUser"
      state_topic: "TankOffsetCurrent"
      min: -100
      max: 100
      step: 0.1
      mode: box
    - name: "Roof Reference Temperature"
      unique_id: "RoofReferenceTemperature_001"
      command_topic: "tempRoofReference"
      min: -20
      max: 120
      step: 0.1
      mode: box
    - name: "Tank Reference Temperature"
      unique_id: "TankReferenceTemperature_001"
      command_topic: "tempTankReference"
      min: -20
      max: 120
      step: 0.1
      mode: box
```

- [ ] **Step 2: YAML sanity check**

Run: `python -c "import yaml; yaml.safe_load(open('HAConfigurationYAML/configuration.yaml'))"`
Expected: no output, exit code 0 (confirms the file is still valid YAML after the edit). If the `yaml` module isn't installed, run `python -m pip show pyyaml` first to confirm; if it's genuinely unavailable, skip this step and instead visually re-check indentation matches the block above exactly (2-space nesting, `-` list items aligned under `number:`).

- [ ] **Step 3: Add documentation to README.md**

Add a short paragraph to the existing "Adjusting sensor calibration offsets via MQTT" section in `README.md` (append after its existing final paragraph, which ends "...nothing crashes."):

```markdown
The Pi also publishes its currently-applied offset back to MQTT on retained
topics `RoofOffsetCurrent`/`TankOffsetCurrent`, once at startup and again
after every accepted change (from either this manual topic or the
automatic reference-correction topics below). The Home Assistant `Roof
Offset`/`Tank Offset` dashboard entities subscribe to these topics, so the
displayed value always matches what's actually applied, regardless of
which source last changed it.
```

- [ ] **Step 4: Commit**

```bash
git add HAConfigurationYAML/configuration.yaml README.md
git commit -m "Add state_topic for HA offset entities and document offset state publish"
```

---

## Self-Review Notes

- Spec coverage: topics + retain (Task 1 Steps 1-6), all four handlers (Task 1 Steps 2-5), startup publish (Task 1 Step 6), HA state_topic on the correct two entities only (Task 2 Step 1), documentation (Task 2 Step 3) — all covered.
- Placeholder scan: none found.
- Type consistency: `MQTT_ROOFOFFSETCURRENT_TOPIC`/`MQTT_TANKOFFSETCURRENT_TOPIC` constant names and `RoofOffsetCurrent`/`TankOffsetCurrent` string values are identical across all publish call sites in Task 1 and the HA config in Task 2.
