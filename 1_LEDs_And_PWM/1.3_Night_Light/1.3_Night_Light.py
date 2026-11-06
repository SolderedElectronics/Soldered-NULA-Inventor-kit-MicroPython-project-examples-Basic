"""
@file       1.3_Night_Light.py
@brief      A night light that fades up as the room gets dark, combining the photoresistor divider from T10 with
            the gamma-corrected PWM from T12. The reading is averaged so the light does not twitch.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, PWM, ADC
import time

# The same night light, with the reading averaged and the brightness gamma corrected.

# The divider junction, and the LED. Both are where they were in T10 and T12, so nothing needs rewiring.
LDR_PIN = 4
LED_PIN = 38

# 5 kHz is far above what the eye can follow. MicroPython's duty_u16 always takes 16 bits, so the brightness
# from 0 to 255 is multiplied by 257 when it is written.
PWM_FREQ = 5000

# The exponential moving average. One number, nudged towards each reading, so the light does not flicker
# when a cloud crosses or someone walks past.
EMA_ALPHA = 0.05

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

# The first reading starts the average, or it would crawl up from zero for the first second.
ema = float(ldr.read())


while True:
    raw = ldr.read()

    # Smooth the reading first, so a hand passing over the sensor does not make the light jump.
    ema = ema + EMA_ALPHA * (raw - ema)

    span = max(1, light_max - light_min)
    wanted = int((light_max - ema) * 255 / span)
    wanted = min(255, max(0, wanted))

    # Gamma correction, the same three lines as in T12. It turns a number that climbs evenly into a brightness that
    # looks like it climbs evenly.
    fraction = wanted / 255.0
    curved = pow(fraction, 2.2)
    written = int(curved * 255.0 + 0.5)

    led.duty_u16(written * 257)

    print("raw {}  ema {:.0f}  wanted {}  written {}".format(raw, ema, wanted, written))
    time.sleep_ms(50)
