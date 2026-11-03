"""
@file       02c_Crossing_Two_Functions.py
@brief      A car traffic light on IO38 to IO40 with a pedestrian light on IO41 and IO42 beside it. The
            pedestrian light is set inside the same four phases, so the two can never both be green.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin
import time

# The five lamps, left to right as they sit on the breadboard, each with its own 330 Ohm resistor.
car_red = Pin(38, Pin.OUT)
car_yellow = Pin(39, Pin.OUT)
car_green = Pin(40, Pin.OUT)
ped_red = Pin(41, Pin.OUT)
ped_green = Pin(42, Pin.OUT)

# How long one step lasts, in milliseconds. Every phase is a multiple of it.
STEP_MS = 500


def set_car_light(red, yellow, green):
    """Set all three car lamps at once, so a combination that does not exist on a real road cannot be written."""
    car_red.value(red)
    car_yellow.value(yellow)
    car_green.value(green)


def set_ped_light(red, green):
    """Set both pedestrian lamps at once, for the same reason."""
    ped_red.value(red)
    ped_green.value(green)


print("CROSSING: the same car light, with a pedestrian light that is its opposite.")

# The pedestrian light is not a second sequence running on its own: it is set inside the same four phases, which is
# what guarantees the two can never both be green.
while True:
    set_car_light(1, 0, 0)  # cars stopped
    set_ped_light(0, 1)  # so people may cross
    time.sleep_ms(STEP_MS * 4)

    set_car_light(1, 1, 0)  # cars getting ready
    set_ped_light(1, 0)  # people already stopped, so the crossing clears first
    time.sleep_ms(STEP_MS * 2)

    set_car_light(0, 0, 1)  # cars moving
    set_ped_light(1, 0)
    time.sleep_ms(STEP_MS * 4)

    set_car_light(0, 1, 0)  # cars slowing
    set_ped_light(1, 0)
    time.sleep_ms(STEP_MS * 2)
