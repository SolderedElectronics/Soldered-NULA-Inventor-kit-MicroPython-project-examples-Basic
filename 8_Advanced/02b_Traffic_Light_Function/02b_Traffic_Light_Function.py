"""
@file       02b_Traffic_Light_Function.py
@brief      A car traffic light on IO38, IO39 and IO40, the four-phase kind: red, red and yellow together,
            green, yellow, and round again.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin
import time

# The three car lamps, left to right as they sit on the breadboard, each with its own 330 Ohm resistor. IO41 and IO42
# are not used here.
car_red = Pin(38, Pin.OUT)
car_yellow = Pin(39, Pin.OUT)
car_green = Pin(40, Pin.OUT)

# How long one step lasts, in milliseconds. Every phase is a multiple of it.
STEP_MS = 500


def set_car_light(red, yellow, green):
    """Set all three car lamps at once, so a combination that does not exist on a real road cannot be written."""
    car_red.value(red)
    car_yellow.value(yellow)
    car_green.value(green)


print("TRAFFIC: red, red and yellow, green, yellow, and round again.")

# Each phase is a whole state of all three lamps rather than a change to one of them, which is what stops the light
# ever showing a combination that does not exist in real life.
while True:
    set_car_light(1, 0, 0)  # red
    time.sleep_ms(STEP_MS * 4)

    set_car_light(1, 1, 0)  # red and yellow, get ready
    time.sleep_ms(STEP_MS * 2)

    set_car_light(0, 0, 1)  # green
    time.sleep_ms(STEP_MS * 4)

    set_car_light(0, 1, 0)  # yellow
    time.sleep_ms(STEP_MS * 2)
