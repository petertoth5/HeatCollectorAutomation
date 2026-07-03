# HeatCollectorAutomation

Automates a solar (sun heat) collector: reads roof-collector and tank temperatures from PTC1000 sensors via a Raspberry Pi + AB Electronics ADCDACPi board, drives a Shelly 1 relay (the collector pump) over MQTT based on the temperature differential, and reports temperatures / estimated power production to Home Assistant.

## How it works

1. `HeatCollectorMain.py` runs an infinite loop, sampling both ADC channels ~7x/sec.
2. Each raw voltage reading is converted to Celsius (PTC1000 linear resistance model) and pushed into a 200-sample circular buffer per sensor; the buffer average is used as the reported temperature.
3. Every ~25 samples the averaged roof/tank temperatures are published to MQTT and fed into the relay control logic:
   - roof temp > tank temp + 7°C → turn pump relay ON
   - roof temp < tank temp + 3°C → turn pump relay OFF
   - otherwise → no change (hysteresis band avoids relay chatter)
4. Every 300s a scheduled job estimates power produced by the collector (Q = m·c·ΔT) using the tank temperature delta over that interval, reported as 0 W if the pump wasn't actually running.
5. Home Assistant consumes the three MQTT sensor topics (`TemperatureRoof`, `TemperatureTank`, `SunCollectorPower`) and derives temperature-difference and cumulative-energy sensors from them.

## Repository structure

```
src/
  main/
    HeatCollectorMain.py            Main control loop (entry point)
    RoofOffset.txt / TankOffset.txt  Calibration offsets applied to raw sensor readings
  SensorManagement/
    ADCHandler.py                   Thin wrapper around the ADCDACPi board (init, single-channel read)
  TemperatureSensing/
    VoltageToTempConverter.py       Voltage -> resistance -> temperature conversion for PTC1000 sensors
    TemperatureFilter.py            CircularBuffer + averaging used to smooth noisy ADC readings
    MeasurementDataPlausibilityChecker.py  Empty placeholder, not yet implemented
  RelayHandling/
    RelayHandling.py                Hysteresis logic that drives the Shelly relay over MQTT
  AuxiliaryFeatures/
    EnergyProductionCalculation.py  Estimates instantaneous power output from the tank temperature delta
    OffsetCalculationAndStorage.py  Reads/writes the calibration offset .txt files
ADCDACPi_Python_test/
  ADCDAC_suncollector_ADC_Test.py   Vendor demo script for exercising the ADC board directly
HAConfigurationYAML/
  configuration.yaml                Home Assistant MQTT sensors + template/integration sensors
HATemplates/
  Sensor value difference.yaml      Standalone HA template sensor snippet (temperature difference)
Design/
  HeatCollectorAutomation_Design.EAP/.ldb  Enterprise Architect model files (system design, binary)
```

## Hardware / integration points

- **Sensors:** two PTC1000 temperature sensors (roof collector, storage tank), read as voltage dividers through the ADCDACPi's two ADC channels (3.3V reference).
- **Actuator:** Shelly 1 relay controlling the collector circulation pump, commanded via MQTT topic `SunCollector_Shelly/command/switch:0`.
- **MQTT broker:** address hardcoded in `HeatCollectorMain.py` (`MQTT_BROKER`); topics are `TemperatureRoof`, `TemperatureTank`, `SunCollectorPower`.
- **Home Assistant:** subscribes to the MQTT topics above; `configuration.yaml` defines the sensors and two derived sensors (temperature difference, integrated/cumulative energy).

## Dependencies

`src/SensorManagement/ADCHandler.py` imports `ADCDACPi`, which is **not** a PyPI
package — it must be installed from the AB Electronics UK library on the target
Raspberry Pi:

```
sudo apt update
sudo apt install python3-build python3-installer git
git clone https://github.com/abelectronicsuk/ABElectronics_Python_Libraries.git
cd ABElectronics_Python_Libraries
python3 -m build
sudo python3 -m installer dist/*.whl
```

(Alternative: copy `ADCDACPi.py` directly into the project directory instead of
installing the package.) I2C must also be enabled on the Pi beforehand. Python 3
only. Repo: https://github.com/abelectronicsuk/ABElectronics_Python_Libraries

## MQTT broker setup (Raspberry Pi)

The script connects to the broker address/port in `MQTT_BROKER`/`MQTT_PORT`
(`src/main/HeatCollectorMain.py`). The typical deployment runs the Mosquitto broker
on the same Raspberry Pi as the script (`MQTT_BROKER = "192.168.1.100"` pointing at
the Pi itself).

Install and enable Mosquitto:

```
sudo apt install mosquitto mosquitto-clients -y
sudo systemctl enable --now mosquitto
```

Verify it's running and listening:

```
sudo systemctl status mosquitto
systemctl is-enabled mosquitto     # should print "enabled" (auto-starts on boot)
ss -tlnp | grep 1883
```

If `systemctl status` shows `Active: failed`/exit-code, check `journalctl -u mosquitto`
or `sudo mosquitto -c /etc/mosquitto/mosquitto.conf -v` for the specific config error —
a common cause is a broken/leftover file under `/etc/mosquitto/conf.d/`.

By default Mosquitto only listens on localhost. Since `HeatCollectorMain.py` runs on
the same Pi as the broker, that's sufficient. If another machine (e.g. Home Assistant)
needs to reach this broker over the network, add a listener config:

```
# /etc/mosquitto/conf.d/listener.conf
listener 1883 0.0.0.0
allow_anonymous true
```

then `sudo systemctl restart mosquitto`. (`allow_anonymous true` has no auth — fine on
a trusted LAN, not for exposure to untrusted networks.)

To uninstall Mosquitto and the `paho-mqtt` Python client entirely (e.g. for a clean
reinstall):

```
sudo systemctl stop mosquitto
sudo systemctl disable mosquitto
sudo apt remove --purge mosquitto mosquitto-clients -y
sudo apt autoremove -y
sudo rm -rf /etc/mosquitto /var/log/mosquitto /var/lib/mosquitto   # only if you want config wiped too

pip3 uninstall paho-mqtt   # or: sudo apt remove --purge python3-paho-mqtt -y
```

If the script raises `ConnectionRefusedError: [Errno 111]` on `mqttc.connect(...)`,
it means nothing is listening at `MQTT_BROKER:MQTT_PORT` — check the broker is
installed, enabled, and running on the host `MQTT_BROKER` actually points to.

## Running as a systemd service (auto-start on boot)

To have `HeatCollectorMain.py` start automatically after every reboot (and restart
itself if it crashes), create a systemd unit:

```
sudo nano /etc/systemd/system/heatcollector.service
```

```ini
[Unit]
Description=Heat Collector Automation
After=network-online.target mosquitto.service
Wants=network-online.target

[Service]
Type=simple
User=<your-user>
WorkingDirectory=/path/to/HeatCollectorAutomation/src/main
ExecStart=/usr/bin/python3 /path/to/HeatCollectorAutomation/src/main/HeatCollectorMain.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Adjust `User`, `WorkingDirectory`, and `ExecStart` paths to match your install
location; point `ExecStart` at a virtualenv's `python3` instead if you use one.
`After=... mosquitto.service` ensures the broker is up before the script tries to
connect.

Enable and start it:

```
sudo systemctl daemon-reload
sudo systemctl enable heatcollector.service
sudo systemctl start heatcollector.service
```

Check status and follow logs:

```
sudo systemctl status heatcollector.service
journalctl -u heatcollector.service -f
```

## Known gaps / TODO

- `MeasurementDataPlausibilityChecker.py` is an empty stub — sensor error flags (`errorFlagRoof`/`errorFlagTank`) are currently set but never used to suppress bad readings or halt relay control.
- No automated tests.
- MQTT broker address and other constants are hardcoded rather than configurable.

See `CLAUDE.md` for guidance on developing this repo with an AI coding agent, and `RESUME.md` for the latest development status.
