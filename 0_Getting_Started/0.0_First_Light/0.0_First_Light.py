"""
@file       0.0_First_Light.py
@brief      The smallest thing the board can do: light the RGB LED that is already on it. Nothing is wired, so
            this proves the cable, the driver, the port and MicroPython itself all work before any circuit exists.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin
import neopixel
import time

# The onboard WS2812B, wired to IO2. It is not brought out to a header, so there is nothing to connect.
RGB_PIN = 2

# How long each colour stays on, in milliseconds.
HOLD_MS = 800

# A quarter brightness. This LED is uncomfortable to look at wide open.
LEVEL = 64

# One LED on the chain. The neopixel module handles the GRB byte order and the strict timing this part needs.
rgb = neopixel.NeoPixel(Pin(RGB_PIN), 1)

print("NULA DeepSleep ESP32-S3 running MicroPython. Cycling the LED on the board.")


# rgb[0] = (red, green, blue) prepares a colour, each value 0 to 255, and rgb.write() sends it to the LED.
while True:
    rgb[0] = (LEVEL, 0, 0)  # red
    rgb.write()
    time.sleep_ms(HOLD_MS)

    rgb[0] = (0, LEVEL, 0)  # green
    rgb.write()
    time.sleep_ms(HOLD_MS)

    rgb[0] = (0, 0, LEVEL)  # blue
    rgb.write()
    time.sleep_ms(HOLD_MS)

    # All three channels off, so there is a clear gap before the next red.
    rgb[0] = (0, 0, 0)
    rgb.write()
    time.sleep_ms(HOLD_MS)
