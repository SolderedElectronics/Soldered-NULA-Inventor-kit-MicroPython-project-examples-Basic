"""
@file       06d_Crude_Night_Light.py
@brief      A night light with no smoothing and no gamma correction, to show what those two corrections fix.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, PWM, ADC
import time

# This is the first program in the kit that does a job rather than demonstrating an idea, and it is made entirely of
# two you have already built. The photoresistor divider is exactly the one from T10, and the PWM output is exactly
# the one from T12.

# The divider junction, and the LED. Both are where they were in T10 and T12, so nothing needs rewiring.
LDR_PIN = 4
LED_PIN = 38

# 5 kHz is far above what the eye can follow. MicroPython's duty_u16 always takes 16 bits, so the brightness
# from 0 to 255 is multiplied by 257 when it is written.
PWM_FREQ = 5000

# Calibration results, in raw ADC counts. They start at the opposite ends so that the first reading replaces both.
light_min = 4095
light_max = 0

# How long the calibration runs for, in milliseconds.
CALIBRATION_MS = 10000

ldr = ADC(Pin(LDR_PIN), atten=ADC.ATTN_11DB)
led = PWM(Pin(LED_PIN), freq=PWM_FREQ)

# Calibration. Watch the light for ten seconds and record the darkest and brightest readings this room produces.
print("Calibrating for 10 seconds. Cover the sensor, then light it.")

start = time.ticks_ms()
while time.ticks_diff(time.ticks_ms(), start) < CALIBRATION_MS:
    raw = ldr.read()
    if raw < light_min:
        light_min = raw
    if raw > light_max:
        light_max = raw
    time.sleep_ms(20)

print("Range: {} to {} counts.".format(light_min, light_max))

# A percentage is only meaningful against a range, so refuse to guess from a range that is not there.
if light_max - light_min < 100:
    print("Range is too narrow to use. Cover the sensor during the calibration, then light it.")


while True:
    raw = ldr.read()

    # Straight from the reading to the pin, with no smoothing and no gamma.
    # Darker room means a higher brightness, so the sums run from the bright end down.
    span = max(1, light_max - light_min)
    brightness = int((light_max - raw) * 255 / span)
    brightness = min(255, max(0, brightness))
    led.duty_u16(brightness * 257)

    print("raw {}  brightness {}".format(raw, brightness))
    time.sleep_ms(50)
