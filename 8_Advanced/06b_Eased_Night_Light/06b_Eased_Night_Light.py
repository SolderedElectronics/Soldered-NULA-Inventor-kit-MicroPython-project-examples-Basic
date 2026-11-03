"""
@file       06b_Eased_Night_Light.py
@brief      A night light that eases towards the brightness the room asks for, so it takes a few seconds to fade rather than following your hand.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, PWM, ADC
import time

# The divider junction, and the LED. Both are where they were in T18, so nothing needs rewiring.
LDR_PIN = 4
LED_PIN = 38

# 5 kHz is far above what the eye can follow.
PWM_FREQ = 5000

# Smooths the reading, as in T18.
EMA_ALPHA = 0.05

# How far the brightness may move on each pass of the loop. At 1 step every 20 ms, a full fade takes about 5 s.
STEP_PER_PASS = 1

# Calibration results, in raw ADC counts.
light_min = 4095
light_max = 0
CALIBRATION_MS = 10000

# The gamma table from the T18 section above.
gamma8 = [int(pow(i / 255.0, 2.2) * 255.0 + 0.5) for i in range(256)]

ldr = ADC(Pin(LDR_PIN), atten=ADC.ATTN_11DB)
led = PWM(Pin(LED_PIN), freq=PWM_FREQ)


def approach(current, target, step):
    """Move current towards target by at most step, and never go past it."""
    if current < target:
        return min(current + step, target)
    if current > target:
        return max(current - step, target)
    return current


def run_calibration():
    """Watch the light for ten seconds and record the darkest and brightest readings this room produces."""
    global light_min, light_max

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
        light_max = light_min + 100


run_calibration()

# The first reading starts the average, or it would crawl up from zero for the first second.
ema = float(ldr.read())

# The brightness the LED is actually showing right now, from 0 to 255.
shown = 0

while True:
    ema = ema + EMA_ALPHA * (ldr.read() - ema)

    # Darker room means a higher brightness, so the sums run from the bright end down.
    span = light_max - light_min
    wanted = int((light_max - ema) * 255 / span)
    wanted = min(255, max(0, wanted))

    # Instead of jumping to what the room asks for, take one small step towards it.
    shown = approach(shown, wanted, STEP_PER_PASS)

    led.duty_u16(gamma8[shown] * 257)

    print("wanted {}  shown {}".format(wanted, shown))
    time.sleep_ms(20)
