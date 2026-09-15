"""
@file       0.1_First_Blink.py
@brief      The first example of the kit. Blinks one LED on IO38 and prints one line to the console, so you can
            confirm the board, the driver and MicroPython itself all work before anything harder.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Soldered Electronics
"""

from machine import Pin
import time

# The LED needs a 330 Ohm resistor in series with it. Example 1.1 works out where that number comes from.
LED_PIN = 38

# On and off time in milliseconds. 500 gives one full blink per second.
DELAY_MS = 500

# Pin.OUT because we write to this pin rather than read it.
led = Pin(LED_PIN, Pin.OUT)

print("NULA DeepSleep ESP32-S3 running MicroPython. Blinking an LED on IO38.")

while True:
    led.value(1)
    time.sleep_ms(DELAY_MS)

    led.value(0)
    time.sleep_ms(DELAY_MS)
