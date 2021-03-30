# Angular Velocity of Earth 7.2921159 × 10-5  radians per SI second

import sys
import smbus
import time
import numpy as np
from datetime import datetime
import csv
import Adafruit_ADS1x15
import sounddevice as sd
from estimate_bpm import BPM_Analyzer

adc = Adafruit_ADS1x15.ADS1115()
bpms = BPM_Analyzer()

ADC_Scale = 4.096/32768.0 

GAIN = 1 
biasVoltage = 1.5 

def getAbsoluteAngle():
    # 0 = Channel 0 minus channel 1
    sin = adc.read_adc_difference(0, gain=GAIN) * ADC_Scale 
    # 3 = Channel 2 minus channel 3
    cos = adc.read_adc_difference(3, gain=GAIN) * ADC_Scale
    # angle = (np.arctan2(sin,cos)*(180/3.1415928353)) + 180
    # Radian
    angle = np.arctan2(sin,cos) + 3.1415928353 
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
filename = 'LX3_BPM_'+(date_now())+'.csv'

# Start_Time = time.time()
Start_Time = time.monotonic()
loop_Time = 15.
loop_cnt = 0
Angle_old = 0
Delta_Angle = 0
Start_Angle = round(getAbsoluteAngle(),6)

print('Angular Velocity & BPM')   
print('{0:<23} {1:<23} {2:<24}'.format('instant','mean','BPM'))

csv = open(filename, 'w')
csv.write('AV instant,AV mean,BPM\n')
csv.close

fs = 44100      # Sample rate
seconds = 3.0    # Duration of recording

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

        audio_input = sd.rec(int(seconds * fs), samplerate=fs, channels=1)
        sd.wait()      
        correlation, bpm = bpms.computeWindowBPM(audio_input.flatten(),fs)

        Angle_old = AbsoluteAngle
        Angular_Velocity_instant = Delta_Angle/loop_Time
        Angular_Velocity_mean = (AbsoluteAngle - Start_Angle)/(loop_cnt*loop_Time)

        if Angular_Velocity_mean:
            print('{0:<23.7E} {1:<23.7E} {2:<24}'.format(Angular_Velocity_instant, Angular_Velocity_mean,str(np.mean(bpm))))
            entry = str(Angular_Velocity_instant) + "," + str(Angular_Velocity_mean) + "," + str(np.mean(bpm)) + "\n"
 
        csv = open(filename, 'a')
        csv.write(entry)

    except KeyboardInterrupt:
        csv.close()
        sys.exit('\nInterrupted by user')     
