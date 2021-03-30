# Angular Velocity of Earth 7.2921159 × 10-5  radians per SI second

import sys
import smbus
import time
import numpy as np
from datetime import datetime
import csv
import Adafruit_ADS1x15

adc = Adafruit_ADS1x15.ADS1115()

ADC_Scale = 4.096/32768.0 

GAIN = 1 
biasVoltage = 1.5 

def getAbsoluteAngle():
    # sin = (adc.read_adc(0, gain=GAIN) * ADC_Scale) - biasVoltage
    # cos = (adc.read_adc(1, gain=GAIN) * ADC_Scale) - biasVoltage

    # 0 = Channel 0 minus channel 1
    sin = adc.read_adc_difference(0, gain=GAIN) * ADC_Scale 
    # 3 = Channel 2 minus channel 3
    cos = adc.read_adc_difference(3, gain=GAIN) * ADC_Scale
    # angle = (np.arctan2(sin,cos)*(180/3.1415928353)) + 180
    # Radian
    angle = np.arctan2(sin,cos) + 3.1415928353 #np.pi 
    return angle

def date_now():
    today = datetime.now().strftime("%Y.%m.%d")
    today = str(today)
    return(today)

def time_now():
    now = datetime.now().strftime("%H:%M:%S")
    now = str(now)
    return(now)

# filename = 'LX3_'+(date_now())+'_'+(time_now())+'.csv'
filename = 'LX3_'+(date_now())+'.csv'

# Start_Time = time.time()
Start_Time = time.monotonic()
loop_Time = 15.
loop_cnt = 0
Angle_old = 0
Delta_Angle = 0
Start_Angle = round(getAbsoluteAngle(),6)

print('Angular Velocity')   
print('{0:<23} {1:<23} {2:<24}'.format('Absolute Angle','instant','mean'))

csv = open(filename, 'w')
csv.write('AV instant,AV mean\n')
csv.close

#polling
while True:
    try:
        if not (np.around(time.monotonic() - Start_Time,3) >= loop_Time):
            continue 
        loop_cnt += 1
        Start_Time = time.monotonic()
        AbsoluteAngle = round(getAbsoluteAngle(),6)
        Delta_Angle = AbsoluteAngle - Angle_old

        if AbsoluteAngle < Start_Angle:
            Start_Angle = AbsoluteAngle
            Angle_old = 0
            loop_cnt = 0
            continue 

        Angle_old = AbsoluteAngle
        Angular_Velocity_instant = Delta_Angle/loop_Time
        Angular_Velocity_mean = (AbsoluteAngle - Start_Angle)/(loop_cnt*loop_Time)

        if Angular_Velocity_mean:
            print('{0:<23.7E} {1:<23.7E} {2:<24.7E}'.format(AbsoluteAngle, Angular_Velocity_instant, Angular_Velocity_mean))
            entry = str(Angular_Velocity_instant) + "," + str(Angular_Velocity_mean) + "\n"
 
        csv = open(filename, 'a')
        csv.write(entry)

        # try:
        #     csv.write(entry)
        # finally:
        #     csv.close()

    except KeyboardInterrupt:
        csv.close()
        # csv = open(filename, 'r')
        # print(csv.read())
        # csv.close()
        sys.exit('\nInterrupted by user')     
