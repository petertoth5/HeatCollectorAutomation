# MQTT Current-Offset State Publish — Design

## Problem

`RoofOffset`/`TankOffset` can now be changed from three sources: the
manual `tempRoofOffsetByUser`/`tempTankOffsetByUser` topics, the automatic
`tempRoofReference`/`tempTankReference` correction topics, and the
`.txt` files read at startup. None of these publish the resulting value
back to MQTT, so the HA dashboard's `Roof Offset`/`Tank Offset` `number`
entities are write-only — they show whatever was last typed into them,
not the real applied offset. This feature makes the Pi publish its
currently-applied offset any time it changes, so HA always reflects the
real device state regardless of what changed it.

## Scope

Two new MQTT topics, publish calls added to four existing handlers plus
one startup publish, and a `state_topic` addition to two existing HA
`number` entities. No new handlers, no new validation, no changes to the
sampling loop or relay logic.

## Topics

| Topic | Publishes | Retained |
|-------|-----------|----------|
| `RoofOffsetCurrent` | current `RoofOffset` value | yes |
| `TankOffsetCurrent` | current `TankOffset` value | yes |

Retained so a freshly (re)subscribed client (e.g. HA after a restart, or a
newly added dashboard) gets the last known value immediately, without
waiting for the next offset change on the Pi.

## Behavior

**At startup**, in `main()`, immediately after `mqttc.connect()` and
`mqttc.loop_start()` (so the client is connected and able to publish),
publish the values already read from `RoofOffset.txt`/`TankOffset.txt`:

```python
mqttc.publish(MQTT_ROOFOFFSETCURRENT_TOPIC, RoofOffset, retain=True)
mqttc.publish(MQTT_TANKOFFSETCURRENT_TOPIC, TankOffset, retain=True)
```

This guarantees a correct retained value exists even on first-ever run or
after a broker's retained state was cleared.

**On every accepted offset change**, in each of the four existing
handlers (`on_roof_offset_message`, `on_tank_offset_message`,
`on_roof_reference_message`, `on_tank_reference_message`), immediately
after the existing `OffsetCalculationAndStorage.write_value(...)` call,
publish the new value:

```python
client.publish(MQTT_ROOFOFFSETCURRENT_TOPIC, RoofOffset, retain=True)
```

(tank equivalent in the tank handlers). `client` is the handler's own
first parameter — in a `message_callback_add` callback this **is** the
connected `mqttc` instance, so no new parameter or global reference is
needed to reach it.

This single mechanism covers all three change sources: a manual HA
dashboard edit and an automatic reference correction both already funnel
through these four handlers, and the startup publish covers the
file-read case. No handler needs to know or care which source triggered
it — "publish after successful write" is the same in a all four.

## HA configuration changes

Add a `state_topic` to the two *existing* `number` entities in
`HAConfigurationYAML/configuration.yaml` (not the new Reference
Temperature entities added in the previous feature — those remain
write-only inputs; the Pi has no "current reference value" to report
back):

```yaml
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
```

## Error handling

None needed beyond what already exists — the published value is already
a validated, finite float that's simultaneously being written to disk by
the same code path. No new failure modes are introduced.

## Testing

No automated test suite in this repo. Verification is manual, on-target:
subscribe to `RoofOffsetCurrent`/`TankOffsetCurrent` (e.g.
`mosquitto_sub -h <broker> -t RoofOffsetCurrent -v`) and confirm a
retained value appears immediately on subscribe, updates after a manual
`tempRoofOffsetByUser` publish, and updates after a
`tempRoofReference` correction. Confirm the HA `Roof Offset`/`Tank Offset`
dashboard cards show the current value after each of those changes and
after an HA restart.

## Documentation

`README.md` gets a short addition to the existing offset sections noting
the new state topics and that the HA `number` entities now reflect the
real applied value.
