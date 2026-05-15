#!/usr/bin/env python

"""
================================================
AB Electronics UK ADC DAC Pi 2-Channel ADC, 2-Channel DAC | ADC Read Demo

run with: python demo_adcread.py
================================================

this demo reads the voltage from channel 1 on the ADC inputs
"""

from __future__ import absolute_import, division, print_function, \
                                                    unicode_literals

from statistics import mean
from dataclasses import dataclass

import time
import os
import paho.mqtt.client as mqtt
import random
import schedule

import sys
sys.path.append('../')

from SensorManagement import ADCHandler
from TemperatureSensing import VoltageToTempConverter
from TemperatureSensing import TemperatureFilter
from RelayHandling import RelayHandling
from AuxiliaryFeatures import EnergyProductionCalculation
from AuxiliaryFeatures import OffsetCalculationAndStorage


@dataclass
class SystemState:
    tank_temp: float = 0.0
    roof_temp: float = 0.0
    tank_temp_init: float = 0.0
    tank_temp_end: float = 0.0
    power_calc_initialized: bool = False
    sun_collector_generating: bool = False
    generating_during_interval: bool = False


# Define Variables
MQTT_BROKER = "192.168.1.100"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL = 45
MQTT_ROOFTEMP_TOPIC = "TemperatureRoof"
MQTT_TANKTEMP_TOPIC = "TemperatureTank"
MQTT_SUNCOLLECTOR_POWER_TOPIC = "SunCollectorPower"
WATER_VOLUME = 30
INTEGRATION_TIME_SECONDS = 300

TankOffset = OffsetCalculationAndStorage.read_and_convert("TankOffset.txt")
RoofOffset = OffsetCalculationAndStorage.read_and_convert("RoofOffset.txt")

# Define on_connect event Handler
def on_connect(mosq, obj, rc):
	print ("Connected to MQTT Broker")

# Define on_publish event Handler
def on_publish(client, userdata, mid):
	print ("Message Published...")

def power_calc_job(mqttc, state: SystemState):
    if not state.power_calc_initialized:
        state.tank_temp_init = state.tank_temp
        state.tank_temp_end = state.tank_temp
        state.power_calc_initialized = True
    else:
        state.tank_temp_init = state.tank_temp_end
        state.tank_temp_end = state.tank_temp

    power_generation = EnergyProductionCalculation.calculate_energy(WATER_VOLUME, state.tank_temp_init, state.tank_temp_end, INTEGRATION_TIME_SECONDS, state.generating_during_interval)
    state.generating_during_interval = False

    mqttc.publish(MQTT_SUNCOLLECTOR_POWER_TOPIC, power_generation)

try:
    from ADCDACPi import ADCDACPi
except ImportError:
    print("Failed to import ADCDACPi from python system path")
    print("Importing from parent folder instead")
    try:
        import sys
        sys.path.append('..')
        from ADCDACPi import ADCDACPi
    except ImportError:
        raise ImportError(
            "Failed to import library from parent folder")


def main():
    '''
    Main program function
    '''

    global TankOffset
    global RoofOffset

    state = SystemState()

    # Initiate MQTT Client
    client_id = f'python-mqtt-{random.randint(0, 1000)}'
    mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id)

    # Register Event Handlers
    mqttc.on_publish = on_publish
    mqttc.on_connect = on_connect

    # Connect with MQTT Broker
    mqttc.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE_INTERVAL)

    schedule.every(INTEGRATION_TIME_SECONDS).seconds.do(power_calc_job, mqttc, state)

    # create an instance of the ADC DAC Pi with a DAC gain set to 1
    adcdac = ADCHandler.initADC()

    circularBufferRoof = TemperatureFilter.CircularBuffer(200)
    circularBufferTank = TemperatureFilter.CircularBuffer(200)
    
    errorFlagRoof = 0
    errorFlagTank = 0

    while True:

        for x in range(100):
            
            uInRoof = ADCHandler.readADCChannelSingle(adcdac,1)
            tempRoof = VoltageToTempConverter.convertADCMeasurementToTemperature(uInRoof) + RoofOffset
            uInTank = ADCHandler.readADCChannelSingle(adcdac,2)
            tempTank = VoltageToTempConverter.convertADCMeasurementToTemperature(uInTank) + TankOffset
            
            if tempRoof != VoltageToTempConverter.ERROR_RETURN_VALUE:
                circularBufferRoof.enqueue(tempRoof)
                errorFlagRoof = 0
            
            else:
                if errorFlagRoof != 1:
                    errorFlagRoof = 1
            
            if tempTank != VoltageToTempConverter.ERROR_RETURN_VALUE:
                circularBufferTank.enqueue(tempTank)
                errorFlagTank = 0
            
            else:
                if errorFlagTank != 1:
                    errorFlagTank = 1
                
            if x % 10 == 0:

                # clear the console
                os.system('clear')

                if errorFlagTank == 1:
                    print("Sensor problem in tank!")

                if errorFlagRoof == 1:
                    print("Sensor problem on roof!")

                print("Everything OK, measurements:")

                state.roof_temp = round(TemperatureFilter.calculate_average(circularBufferRoof), 1)
                print("Roof Temp:")
                print(state.roof_temp, " Celsius")

                state.tank_temp = round(TemperatureFilter.calculate_average(circularBufferTank), 1)
                print("Tank Temp:")
                print(state.tank_temp, " Celsius")
                
            if x % 25 == 0:
                # Publish message to MQTT Topic
                mqttc.publish(MQTT_ROOFTEMP_TOPIC, state.roof_temp)

                # Publish message to MQTT Topic
                mqttc.publish(MQTT_TANKTEMP_TOPIC, state.tank_temp)

                if "Relay ON" == RelayHandling.temperature_control(state.roof_temp, state.tank_temp, mqttc):
                    state.sun_collector_generating = True
                    state.generating_during_interval = True
                else:
                    state.sun_collector_generating = False

                schedule.run_pending()
                    
            time.sleep(0.15)

if __name__ == "__main__":
    main()
