"""
@file       04d_Smoothed_Light_Switch.py
@brief      Smooths the photoresistor with a moving average, learns the darkest and brightest light it has seen,
            and switches an LED on two thresholds so it cannot flicker.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, ADC
import time

LDR_PIN = 4
LED_PIN = 38

# The moving average from T11. Smaller means heavier smoothing and a slower response.
EMA_ALPHA = 0.1

# The two thresholds from T15, as a percentage of the range the script has seen so far.
THRESHOLD_PCT = 50
HYSTERESIS_PCT = 8

# The range is never allowed to be narrower than this many counts, so the very first readings do not
# get stretched across the whole 0 to 100 scale.
MIN_SPAN = 200

ldr = ADC(Pin(LDR_PIN), atten=ADC.ATTN_11DB)
led = Pin(LED_PIN, Pin.OUT)

# Start the average and the range at the first reading.
smooth = float(ldr.read())
light_min = smooth  # the darkest smoothed reading seen so far
light_max = smooth  # the brightest smoothed reading seen so far
led_on = False


# Turns the smoothed reading into a percentage of the range seen so far.
def light_percent():
    span = max(light_max - light_min, MIN_SPAN)
    pct = int((smooth - light_min) * 100 / span)
    return max(0, min(100, pct))


while True:
    # Move the average a small step towards the new reading.
    smooth = smooth + EMA_ALPHA * (ldr.read() - smooth)

    # Widen the range if this reading is darker or brighter than anything seen before.
    light_min = min(light_min, smooth)
    light_max = max(light_max, smooth)

    pct = light_percent()

    # Switch on only above the upper number and off only below the lower one. In between, nothing changes.
    if not led_on and pct > THRESHOLD_PCT + HYSTERESIS_PCT:
        led_on = True
    elif led_on and pct < THRESHOLD_PCT - HYSTERESIS_PCT:
        led_on = False

    led.value(1 if led_on else 0)

    # Two numbers per line for the plotter: the light as a percentage, and the LED as 100 when on and 0 when off.
    print(pct, 100 if led_on else 0)

    time.sleep_ms(20)
