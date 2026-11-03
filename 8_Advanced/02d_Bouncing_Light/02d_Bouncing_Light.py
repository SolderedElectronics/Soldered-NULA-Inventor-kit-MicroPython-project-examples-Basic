"""
@file       02d_Bouncing_Light.py
@brief      A lit spot that travels along five LEDs on IO38 to IO42 and turns round at each end, so it bounces
            from side to side. Uses the same wiring as the running light.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin
import time

# The five LEDs, left to right as they sit on the breadboard, each with its own 330 Ohm resistor.
LED_PINS = (38, 39, 40, 41, 42)
leds = [Pin(p, Pin.OUT) for p in LED_PINS]

# How long the spot stays on each LED, in milliseconds. Shorter than the running light, so the bounce looks smooth.
STEP_MS = 150

# Which LED is lit, and which way the spot is heading: 1 is to the right, -1 is to the left.
position = 0
direction = 1

print("BOUNCE: a lit spot travels along the row and turns round at each end.")

while True:
    # Light only the LED at the current position.
    for i in range(len(leds)):
        leds[i].value(1 if i == position else 0)
    time.sleep_ms(STEP_MS)

    # Take one step in the current direction.
    position = position + direction

    # On reaching either end, turn round, so the next step goes back the way the spot came.
    if position == 0 or position == len(leds) - 1:
        direction = -direction
