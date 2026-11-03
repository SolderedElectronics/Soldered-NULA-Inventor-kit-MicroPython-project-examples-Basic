"""
@file       05d_Colour_Cycle.py
@brief      Cycles the onboard RGB LED round the colour wheel by itself, with the pot setting how fast.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, ADC
import neopixel
import time

# The pot's wiper, same pin as T10 used.
POT_PIN = 4

# The onboard WS2812B, wired to IO2 through a 1 kOhm series resistor. Not brought out to a header.
RGB_PIN = 2

# Fixed so the pot changes one thing only: how fast the colour moves. A quarter brightness is plenty.
SATURATION = 1.0
BRIGHTNESS = 0.25


def hsv_to_rgb(h, s, v):
    """Convert a hue in degrees, saturation and value into three 0-255 channel levels.
    The same function as in the T17 section above."""
    c = v * s
    x = c * (1.0 - abs((h / 60.0) % 2.0 - 1.0))
    m = v - c

    if h < 60:
        rf, gf, bf = c, x, 0.0
    elif h < 120:
        rf, gf, bf = x, c, 0.0
    elif h < 180:
        rf, gf, bf = 0.0, c, x
    elif h < 240:
        rf, gf, bf = 0.0, x, c
    elif h < 300:
        rf, gf, bf = x, 0.0, c
    else:
        rf, gf, bf = c, 0.0, x

    return (int((rf + m) * 255), int((gf + m) * 255), int((bf + m) * 255))


pot = ADC(Pin(POT_PIN), atten=ADC.ATTN_11DB)
rgb = neopixel.NeoPixel(Pin(RGB_PIN), 1)

# Where we are on the colour wheel, in degrees, and when we last moved it.
hue = 0.0
last_ms = time.ticks_ms()

print("Colour cycle: speed on IO4.")

while True:
    # The knob sets a speed from 0 to 360 degrees per second, so a full turn of the knob is one lap of the wheel
    # every second.
    degrees_per_second = (pot.read() / 4095.0) * 360.0

    # Move the hue by speed times the time that has passed, so the speed stays the same however long the loop takes.
    now = time.ticks_ms()
    elapsed_seconds = time.ticks_diff(now, last_ms) / 1000.0
    last_ms = now

    # The remainder (%) wraps the hue round at the end of the wheel.
    hue = (hue + degrees_per_second * elapsed_seconds) % 360.0

    rgb[0] = hsv_to_rgb(hue, SATURATION, BRIGHTNESS)
    rgb.write()

    time.sleep_ms(20)
