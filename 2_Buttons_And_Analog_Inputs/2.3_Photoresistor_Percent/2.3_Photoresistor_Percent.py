"""
@file       2.3_Photoresistor_Percent.py
@brief      Calibrates the light range over ten seconds, then reports the light as a percentage of that range.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, ADC
import time

LDR_PIN = 4

ldr = ADC(Pin(LDR_PIN), atten=ADC.ATTN_11DB)

# Ten seconds of hand-waving, keeping the lowest and highest readings seen. A percentage of this sensor's range in
# this room is honest; converting to lux would be a fiction, because a photoresistor is not linear in light level.
print()
print("CALIBRATING for 10 seconds. Cover the sensor, then light it up.")

light_min = 4095
light_max = 0

start = time.ticks_ms()
while time.ticks_diff(time.ticks_ms(), start) < 10000:
    raw = ldr.read()
    if raw < light_min:
        light_min = raw
    if raw > light_max:
        light_max = raw
    time.sleep_ms(5)

# A range of zero would make every later division fail.
if light_max - light_min < 10:
    light_max = light_min + 10

print("Range: {} to {}".format(light_min, light_max))
print()


while True:
    # Read the light and turn it into a percentage of the range you calibrated, from 0 (darkest) to 100 (brightest).
    raw = ldr.read()
    pct = (raw - light_min) * 100 // (light_max - light_min)
    if pct < 0:
        pct = 0
    if pct > 100:
        pct = 100

    print(pct)
    time.sleep_ms(100)
