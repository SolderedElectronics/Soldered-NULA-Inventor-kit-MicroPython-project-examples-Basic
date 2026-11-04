"""
@file       06e_Self_Calibrating_Night_Light.py
@brief      A night light with no calibration step. It keeps track of the darkest and brightest light it has seen
            and lets those limits drift slowly inwards, so a change of room ends up calibrated by itself.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, PWM, ADC
import time

# The divider junction, and the LED. Both are where they were in T13, so nothing needs rewiring.
LDR_PIN = 4
LED_PIN = 38

# 5 kHz is far above what the eye can follow.
PWM_FREQ = 5000

# Smooths the reading, as in T13.
EMA_ALPHA = 0.05

# Every DECAY_MS each limit moves 1 count towards the current reading. At 2000 ms that is 30 counts a minute, so a
# limit that is 600 counts out of date takes about 20 minutes to come in.
DECAY_MS = 2000

# The two limits never come closer than this. Without a floor, a steady room would shrink the range until the
# smallest flicker swung the LED from dark to full brightness.
MIN_SPAN = 200

# How often the range and the brightness are printed.
PRINT_MS = 1000

# The gamma table from T13.
gamma8 = [int(pow(i / 255.0, 2.2) * 255.0 + 0.5) for i in range(256)]

ldr = ADC(Pin(LDR_PIN), atten=ADC.ATTN_11DB)
led = PWM(Pin(LED_PIN), freq=PWM_FREQ)

# The first reading starts the average, and a small range centred on it is the first guess. The range grows
# as soon as the room gets darker or brighter than that.
ema = float(ldr.read())
light_min = int(ema) - MIN_SPAN // 2
light_max = int(ema) + MIN_SPAN // 2

last_decay_ms = time.ticks_ms()
last_print_ms = time.ticks_ms()


def update_range(reading):
    """Keep light_min and light_max around the readings of the last few minutes. A reading outside the range widens
    it at once. Otherwise, every DECAY_MS, each limit takes one step towards the current reading."""
    global light_min, light_max, last_decay_ms

    if reading < light_min:
        light_min = reading
    if reading > light_max:
        light_max = reading

    if time.ticks_diff(time.ticks_ms(), last_decay_ms) >= DECAY_MS:
        last_decay_ms = time.ticks_ms()

        # Only shrink while the range is wider than the floor.
        if light_max - light_min > MIN_SPAN:
            if light_min < reading:
                light_min += 1
            if light_max > reading:
                light_max -= 1


print("ADAPTIVE: no calibration, the range is learned while the night light runs.")

while True:
    ema = ema + EMA_ALPHA * (ldr.read() - ema)
    smoothed = int(ema)

    # Stretch the range if the room went past it, and let it drift inwards a little if it did not.
    update_range(smoothed)

    # Darker room means a higher brightness, so the two ends of the scale are the other way round, as in T13.
    clamped = min(light_max, max(light_min, smoothed))
    brightness = 255 - (clamped - light_min) * 255 // (light_max - light_min)
    led.duty_u16(gamma8[brightness] * 257)

    # Print once a second, using the clock instead of sleeping so the LED keeps following the light.
    if time.ticks_diff(time.ticks_ms(), last_print_ms) >= PRINT_MS:
        last_print_ms = time.ticks_ms()
        print("range {} to {}  brightness {}".format(light_min, light_max, brightness))

    time.sleep_ms(20)
