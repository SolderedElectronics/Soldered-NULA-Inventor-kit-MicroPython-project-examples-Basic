"""
@file       0.1_Two_LEDs_Taking_Turns.py
@brief      Two LEDs on IO38 and IO39 taking turns. One is always lit and the other is always dark, and they swap
            every half second.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin
import time

# The two LEDs, each with its own 330 Ohm resistor in series.
led_a = Pin(38, Pin.OUT)
led_b = Pin(39, Pin.OUT)

# How long one turn lasts, in milliseconds.
STEP_MS = 500

print("ALTERNATE: two LEDs take turns. One is always lit.")

while True:
    # The second LED is always given the opposite of the first.
    led_a.value(1)
    led_b.value(0)
    time.sleep_ms(STEP_MS)

    led_a.value(0)
    led_b.value(1)
    time.sleep_ms(STEP_MS)
