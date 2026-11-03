"""
@file       06c_Dusk_Switch.py
@brief      A night light that switches fully on when the room gets dark and fully off when it is light again, fading both ways.
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

# The light level as a percentage of the calibrated range, 0 for the darkest you showed it and 100 for the
# brightest. The lamp comes on below 35 and goes off only above 50. The gap between the two stops it flickering
# on and off when the room sits right at the edge.
ON_BELOW = 35
OFF_ABOVE = 50

# How far the brightness may move on each pass: 2 steps every 20 ms is about 2.5 s for a full fade.
STEP_PER_PASS = 2

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

ema = float(ldr.read())

# Whether the lamp is meant to be on, and the brightness it is showing right now.
lamp_on = False
shown = 0

while True:
    ema = ema + EMA_ALPHA * (ldr.read() - ema)

    # The light level as a percentage of the room's own range.
    span = light_max - light_min
    percent = int((ema - light_min) * 100 / span)
    percent = min(100, max(0, percent))

    # Two different limits depending on the current state: this is called hysteresis.
    if not lamp_on and percent < ON_BELOW:
        lamp_on = True
    elif lamp_on and percent > OFF_ABOVE:
        lamp_on = False

    # The lamp is either fully on or fully off, and the fade does the rest.
    target = 255 if lamp_on else 0
    shown = approach(shown, target, STEP_PER_PASS)

    led.duty_u16(gamma8[shown] * 257)

    print("light {} %  lamp {}".format(percent, "on" if lamp_on else "off"))
    time.sleep_ms(20)
