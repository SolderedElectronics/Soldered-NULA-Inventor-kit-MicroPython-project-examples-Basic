"""
@file       02e_Table_Crossing.py
@brief      A car traffic light on IO38 to IO40 with a pedestrian light on IO41 and IO42, where the whole
            sequence is a table. Each row says which lamps are on and for how many steps.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin
import time

# The five lamps, left to right as they sit on the breadboard, each with its own 330 Ohm resistor.
# In order: car red, car yellow, car green, pedestrian red, pedestrian green.
LAMP_PINS = (38, 39, 40, 41, 42)
lamps = [Pin(p, Pin.OUT) for p in LAMP_PINS]

# How long one step lasts, in milliseconds.
STEP_MS = 500

# The whole sequence. A row is only ever one complete state of all five lamps, so the two lights can never be
# green together unless a row says so, and no row does. Each row is (lamp states, steps).
PHASES = (
    ((1, 0, 0, 0, 1), 4),  # cars stopped, people may cross
    ((1, 1, 0, 1, 0), 2),  # cars getting ready, people stopped
    ((0, 0, 1, 1, 0), 4),  # cars going
    ((0, 1, 0, 1, 0), 2),  # cars slowing
)

print("TABLE: the crossing runs from a table of phases.")

while True:
    # Show each row of the table in turn, then start again.
    for states, steps in PHASES:
        # Write all five lamps from this row.
        for lamp, state in zip(lamps, states):
            lamp.value(state)
        time.sleep_ms(STEP_MS * steps)
