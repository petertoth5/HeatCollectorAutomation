# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

HeatCollectorAutomation automates a solar heat collector control system via Raspberry Pi and Shelly 1 relay over MQTT. The system monitors roof and tank temperatures, calculates energy production, and controls a relay pump to optimize heat transfer.

**Key integrations:** MQTT broker, ADC/DAC hardware (AB Electronics Pi), PTC temperature sensors, Shelly 1 relay, Home Assistant (YAML templates).

## Architecture

### Core Control Flow

Entry point: `src/main/HeatCollectorMain.py`
- Reads ADC voltages from roof and tank temperature sensors
- Applies temperature filtering and offset calibration
- Performs plausibility checks on measurements
- Publishes temperatures and calculated power to MQTT
- Runs scheduled jobs (power calculation every 5 minutes)
- Controls relay via temperature differential logic

### Module Structure

- **SensorManagement/ADCHandler**: ADC initialization (3.3V ref), single-channel voltage reads
- **TemperatureSensing**: Converts ADC voltage → resistance → temperature (PTC1000 sensor with linear fit: y = 3.817x + 994.667); circular-buffer filtering; plausibility checks (error value: 1000°C)
- **RelayHandling**: Relay control logic — ON if roof_temp > tank_temp + 7°C, OFF if roof_temp < tank_temp + 3°C (hysteresis prevents chatter)
- **AuxiliaryFeatures**: Energy calculation (Q = m·c·ΔT, only report positive watts when pump is generating), offset storage/retrieval for calibration
- **ADCDACPi**: External hardware library (AB Electronics Pi ADC/DAC); import fallback handles path variations

### Data Flow

```
ADC voltage → VoltageToTempConverter → TemperatureFilter (circular buffer) 
  → MeasurementDataPlausibilityChecker → Main loop → RelayHandling control
                                                    → EnergyProductionCalculation 
                                                    → MQTT publish
```

Offsets (TankOffset.txt, RoofOffset.txt) applied after plausibility check.

### MQTT Topics

- `TemperatureRoof`: Roof temperature (°C) — published by main, consumed by Home Assistant
- `TemperatureTank`: Tank temperature (°C) — published by main, consumed by Home Assistant
- `SunCollectorPower`: Power in watts — published every 5 minutes after calculation
- `SunCollector_Shelly/command/switch:0`: Relay on/off commands ("on"/"off")

Home Assistant consumes these sensors and calculates temperature difference and energy integration.

## Development Setup

**Python environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows
pip install paho-mqtt schedule
```

**ADCDACPi library:**
- Installed separately on Raspberry Pi or copied to parent directory
- Import fallback in main: tries direct import, then `sys.path.append('../')` for relative path

**Offset files** (`src/main/TankOffset.txt`, `src/main/RoofOffset.txt`):
- Must exist before running — contain single float value (calibration offset in °C)
- Initialize: `echo "0.0" > src/main/TankOffset.txt && echo "0.0" > src/main/RoofOffset.txt`

## Running the Application

**Main application** (Raspberry Pi with ADC hardware):
```bash
cd src/main && python HeatCollectorMain.py
```

**Hardware test utility:**
```bash
python ADCDACPi_Python_test/ADCDAC_suncollector_ADC_Test.py
```

**MQTT broker requirement:**
- Must run at `192.168.1.100:1883` (hardcoded in main)
- Use mosquitto or Home Assistant built-in broker

## Testing Without Hardware

No unit test framework present. Two approaches:

1. **Stub ADC/relay**: Import ADC/relay modules and mock voltage readings or relay commands before calling main logic
2. **Dry-run on Pi**: Deploy to Pi without water flow; relay engages/disengages based on simulated ambient temperature changes

Temperature modules (`VoltageToTempConverter`, `TemperatureFilter`, `MeasurementDataPlausibilityChecker`) can be tested independently by providing mock ADC voltages (0–3.3V range).

## Key Configuration Values

Located in `src/main/HeatCollectorMain.py`:
- `WATER_VOLUME = 30` liters (tank capacity)
- `INTEGRATION_TIME_SECONDS = 300` (5-minute power calculation interval)
- Relay hysteresis: ON at +7°C diff, OFF at +3°C diff (prevents rapid switching)
- Temperature sensor: PTC1000 with constants `A_COEFF=3.817`, `B_COEFF=994.667`, `R2_RESISTANCE=1515Ω`, `U_IN=5V`
- ADC reference voltage: 3.3V (must match actual Pi rail voltage)

## Important Invariants

1. **Offset files** (`TankOffset.txt`, `RoofOffset.txt`) must exist in `src/main/` and contain single float values — no error handling if missing or unparseable — initialize with `echo "0.0" > src/main/TankOffset.txt`
2. **PTC sensor linearity**: Temperature calculation assumes linear resistance-to-temperature relationship; invalid ADC readings default to 1000°C error value
3. **Power calculation gating**: Only reports positive watts when `SunCollectorGenerating` flag is True (relay is ON)
4. **Circular buffer**: Temperature filter uses fixed-size circular buffer — capacity set at initialization
5. **Global state** in main: Temperature tracking across scheduled jobs (`TankTempInit`, `TankTempEnd`, `PowerCalculationInitialized`, `SunCollectorGenerating`)
6. **Import path management**: Modules import relative to `src/main/` via `sys.path.append('../')` — paths change if deployment structure differs

## Home Assistant Integration

Configuration in `HAConfigurationYAML/configuration.yaml`:
- MQTT sensors map to `TemperatureTank`, `TemperatureRoof`, `SunCollectorPower`
- Template sensor calculates temperature difference
- Integration sensor accumulates power over time (kWh)
- Max sub-interval: 5 minutes (skips power calc if MQTT message delayed)

## Common Edits

- **Relay thresholds**: Modify ON/OFF constants in `RelayHandling.py` (currently ±7°C / ±3°C)
- **Power interval**: Change `INTEGRATION_TIME_SECONDS` in main (currently 300s)
- **Tank volume**: Update `WATER_VOLUME` in main (currently 30L)
- **Sensor calibration**: Update offset files or sensor coefficients in `VoltageToTempConverter.py`
- **MQTT broker/topics**: Hardcoded in main — update if infrastructure changes

## Testing Notes

- No unit tests present; testing relies on hardware integration or stubbing ADC/relay
- ADC test utility available for hardware validation
- Temperature plausibility checker catches obviously bad readings (> 1000°C)
