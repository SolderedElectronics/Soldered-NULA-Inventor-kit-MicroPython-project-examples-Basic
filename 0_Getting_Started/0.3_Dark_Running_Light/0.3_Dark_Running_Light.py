"""
@file       0.3_Dark_Running_Light.py
@brief      A dark spot walking along five lit LEDs on IO38 to IO42. Each LED goes dark for half a second in turn.
            The other four stay lit.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin
import time

# The five LEDs, left to right as they sit on the breadboard, each with its own 330 Ohm resistor. Every pin is an
# output.
led_1 = Pin(38, Pin.OUT)
led_2 = Pin(39, Pin.OUT)
led_3 = Pin(40, Pin.OUT)
led_4 = Pin(41, Pin.OUT)
led_5 = Pin(42, Pin.OUT)

# How long each LED stays in its state, in milliseconds.
STEP_MS = 500

# Start with all five lit, so each one only has to go dark in its turn.
led_1.value(1)
led_2.value(1)
led_3.value(1)
led_4.value(1)
led_5.value(1)

print("RUNNING: a dark spot walks along the lit row and starts again.")

while True:
    led_1.value(0)
    time.sleep_ms(STEP_MS)
    led_1.value(1)

    led_2.value(0)
    time.sleep_ms(STEP_MS)
    led_2.value(1)

    led_3.value(0)
    time.sleep_ms(STEP_MS)
    led_3.value(1)

    led_4.value(0)
    time.sleep_ms(STEP_MS)
    led_4.value(1)

    led_5.value(0)
    time.sleep_ms(STEP_MS)
    led_5.value(1)
