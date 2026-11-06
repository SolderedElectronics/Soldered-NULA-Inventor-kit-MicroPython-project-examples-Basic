"""
@file       2.3_Photoresistor_Hysteresis.py
@brief      Calibrates the light range, then switches an LED on two thresholds, so light sitting right on the switching
            point cannot make it flicker.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, ADC
import time

LDR_PIN = 4
LED_PIN = 38

# Thresholds, as a percentage of the calibrated range.
THRESHOLD_PCT = 50
HYSTERESIS_PCT = 8

ldr = ADC(Pin(LDR_PIN), atten=ADC.ATTN_11DB)
led = Pin(LED_PIN, Pin.OUT)

led_on = False

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
    # Switching on takes more light than switching off, so noise cannot move the output back. Same mechanism as
    # the relay in T23 and the thermostat in T26.
    # Read the light and turn it into a percentage of the range you calibrated, from 0 (darkest) to 100 (brightest).
    raw = ldr.read()
    pct = (raw - light_min) * 100 // (light_max - light_min)
    if pct < 0:
        pct = 0
    if pct > 100:
        pct = 100

    on_above = THRESHOLD_PCT + HYSTERESIS_PCT
    off_below = THRESHOLD_PCT - HYSTERESIS_PCT

    # Switch on only above the upper number and off only below the lower one. In between, nothing changes.
    if not led_on and pct > on_above:
        led_on = True
        led.value(1)
    elif led_on and pct < off_below:
        led_on = False
        led.value(0)

    # The light as a percentage, then the LED as 100 when it is on and 0 when it is off.
    if led_on:
        print(pct, 100)
    else:
        print(pct, 0)
    time.sleep_ms(50)
