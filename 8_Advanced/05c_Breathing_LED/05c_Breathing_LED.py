"""
@file       05c_Breathing_LED.py
@brief      Makes the LED on IO38 breathe in and out smoothly, using a gamma table so the breath looks even.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, PWM
import math
import time

# The LED on IO38 needs a 330 Ohm resistor in series or it will be damaged.
LED_PIN = 38

# 5 kHz is far above what the eye can follow.
PWM_FREQ = 5000

# How long one whole breath takes, in milliseconds: up, then back down.
BREATH_MS = 4000

# The same gamma table as in the T16 section above. It bends an even number into an even-looking brightness.
gamma8 = [int(pow(i / 255.0, 2.2) * 255.0 + 0.5) for i in range(256)]

# MicroPython's duty is 16-bit, 0 to 65535, so an 8-bit table value is multiplied by 257 to cover the same range.
led = PWM(Pin(LED_PIN), freq=PWM_FREQ, duty_u16=0)

print("Breathing LED on IO38.")

while True:
    # How far through the current breath we are, as an angle from 0 to a full circle (2 * pi is about 6.28).
    # The remainder (%) makes the time start again from 0 every BREATH_MS.
    phase = (time.ticks_ms() % BREATH_MS) / BREATH_MS * 2 * math.pi

    # sin() swings between -1 and 1. Adding 1 and halving it gives a number that swings smoothly between 0 and 1.
    level = (math.sin(phase) + 1.0) / 2.0

    # Turn 0 to 1 into 0 to 255, bend it through the gamma table and send it to the LED.
    led.duty_u16(gamma8[int(level * 255)] * 257)

    time.sleep_ms(10)
