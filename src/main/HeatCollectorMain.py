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

import time
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

# Define Variables
MQTT_BROKER = "192.168.1.100"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL = 45
MQTT_ROOFTEMP_TOPIC = "TemperatureRoof"
MQTT_TANKTEMP_TOPIC = "TemperatureTank"
MQTT_SUNCOLLECTOR_POWER_TOPIC = "SunCollectorPower"
WATER_VOLUME = 30
INTEGRATION_TIME_SECONDS = 300

# Global variables for temperatures tobe able to pass them to scheduled job.
TankTempInit = 0
TankTempEnd = 0
PowerCalculationInitialized = False
SunCollectorGenerating = False

TankTemp = 0
RoofTemp = 0

TankOffset = OffsetCalculationAndStorage.read_and_convert("TankOffset.txt")
RoofOffset = OffsetCalculationAndStorage.read_and_convert("RoofOffset.txt")

# Define on_connect event Handler
def on_connect(mosq, obj, rc):
	print ("Connected to MQTT Broker")

# Define on_publish event Handler
def on_publish(client, userdata, mid):
	print ("Message Published...")

def power_calc_job(mqttc):

    global TankTempInit, TankTempEnd, PowerCalculationInitialized, SunCollectorGenerating

    if (PowerCalculationInitialized == False):
        TankTempInit                = TankTemp
        TankTempEnd                 = TankTemp
        PowerCalculationInitialized = True
    else:
        TankTempInit    = TankTempEnd
        TankTempEnd     = TankTemp

    power_generation = EnergyProductionCalculation.calculate_energy(WATER_VOLUME, TankTempInit, TankTempEnd, INTEGRATION_TIME_SECONDS, SunCollectorGenerating)
    
    # Publish message to MQTT Topic 
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
    
    global TankTemp
    global RoofTemp
    global SunCollectorGenerating
    global TankOffset
    global RoofOffset

    # Initiate MQTT Client
    client_id = f'python-mqtt-{random.randint(0, 1000)}'
    mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id)

    # Register Event Handlers
    mqttc.on_publish = on_publish
    mqttc.on_connect = on_connect

    # Connect with MQTT Broker
    mqttc.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE_INTERVAL) 

    schedule.every(INTEGRATION_TIME_SECONDS).seconds.do(power_calc_job, mqttc)

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

                # clear the console (ANSI escape, avoids spawning a subprocess like os.system('clear'))
                print("\033[H\033[J", end="")

                if errorFlagTank == 1:
                    print("Sensor problem in tank!")
                    
                if errorFlagRoof == 1:
                    print("Sensor problem on roof!")
                
                print("Everything OK, measurements:")

                RoofTemp = round(TemperatureFilter.calculate_average(circularBufferRoof), 1)
                print("Roof Temp:")
                print(RoofTemp, " Celsius")

                TankTemp = round(TemperatureFilter.calculate_average(circularBufferTank), 1)
                print("Tank Temp:")
                print(TankTemp, " Celsius")
                
            if x % 25 == 0:
                # Recompute averages here too: 25 is not a multiple of 10, so relying on the
                # x % 10 block alone would publish stale Roof/TankTemp values on these iterations.
                RoofTemp = round(TemperatureFilter.calculate_average(circularBufferRoof), 1)
                TankTemp = round(TemperatureFilter.calculate_average(circularBufferTank), 1)

                # Publish message to MQTT Topic
                mqttc.publish(MQTT_ROOFTEMP_TOPIC, RoofTemp)
                
                # Publish message to MQTT Topic 
                mqttc.publish(MQTT_TANKTEMP_TOPIC, TankTemp)

                if "Relay ON" == RelayHandling.temperature_control(RoofTemp, TankTemp, mqttc):
                    SunCollectorGenerating = True
                else:
                    SunCollectorGenerating = False

                schedule.run_pending()
                    
            time.sleep(0.15)

if __name__ == "__main__":
    main()
