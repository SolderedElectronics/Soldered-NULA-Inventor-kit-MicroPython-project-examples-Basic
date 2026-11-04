"""
@file       05b_Colour_Function.py
@brief      Drives the onboard WS2812B from one pot feeding the hue.
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

# Fixed so the pot changes one thing only. A quarter brightness is plenty: the onboard LED is uncomfortable
# to look at wide open.
SATURATION = 1.0
BRIGHTNESS = 0.25


def hsv_to_rgb(h, s, v):
    """Convert a hue in degrees, saturation and value into three 0-255 channel levels."""
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

# The LED is a WS2812B: IO2 sends it a serial message rather than a voltage, and a controller inside the
# package sets the three channels. The neopixel module handles the GRB byte order and the strict timing.
rgb = neopixel.NeoPixel(Pin(RGB_PIN), 1)

print("Colour: hue on IO4.")

while True:
    raw = pot.read()

    # Hue is the colour as an angle: 0 red, 120 green, 240 blue, 360 back to red. One knob walks through every
    # colour there is, which three separate red, green and blue levels could not do.
    hue = (raw / 4095.0) * 360.0

    rgb[0] = hsv_to_rgb(hue, SATURATION, BRIGHTNESS)
    rgb.write()

    time.sleep_ms(20)

# Before section 6: opening the JP1 solder jumper disconnects this LED to stop its leakage during deep sleep,
# and this script then does nothing at all.
