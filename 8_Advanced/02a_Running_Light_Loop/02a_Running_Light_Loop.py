"""
@file       02a_Running_Light_Loop.py
@brief      A lit spot walking along a row of five LEDs on IO38 to IO42. It steps one LED to the right every half
            second and starts again at the left after the last one.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin
import time

# Five LEDs on five pins, left to right as they sit on the breadboard, each with its own 330 Ohm resistor. IO38 to IO42
# are next to each other on the header, none of them has an analog input on it, and nothing on the board uses them.
LED_PINS = (38, 39, 40, 41, 42)

# How long one step lasts, in milliseconds.
STEP_MS = 500

# Every one of the five pins is an output.
leds = [Pin(p, Pin.OUT) for p in LED_PINS]

# Where the lit spot currently is. It has to survive from one pass of the loop to the next, so it is set up before
# the loop starts.
running_position = 0


def all_off():
    """Every LED dark."""
    for led in leds:
        led.value(0)


print("RUNNING: a lit spot walks along the row and starts again.")

while True:
    # Everything off, so only the new position is lit and the old one does not have to be cleared by name.
    all_off()

    leds[running_position].value(1)
    time.sleep_ms(STEP_MS)

    # Step along, and wrap back to the start after the last LED.
    running_position = running_position + 1
    if running_position >= len(leds):
        running_position = 0
