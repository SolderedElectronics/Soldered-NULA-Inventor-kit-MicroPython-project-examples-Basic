"""
@file       04c_Hysteresis_Helper_Function.py
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


# Turns a reading into a percentage of the range you calibrated, from 0 (darkest) to 100 (brightest).
def light_percent():
    raw = ldr.read()
    pct = (raw - light_min) * 100 // (light_max - light_min)
    return max(0, min(100, pct))


while True:
    # Switching on takes more light than switching off, so noise cannot move the output back. Same mechanism as
    # the relay in T30 and the thermostat in T33.
    pct = light_percent()

    on_above = THRESHOLD_PCT + HYSTERESIS_PCT
    off_below = THRESHOLD_PCT - HYSTERESIS_PCT

    if not led_on and pct > on_above:
        led_on = True
    elif led_on and pct < off_below:
        led_on = False

    led.value(1 if led_on else 0)

    print(pct, 100 if led_on else 0)
    time.sleep_ms(50)
