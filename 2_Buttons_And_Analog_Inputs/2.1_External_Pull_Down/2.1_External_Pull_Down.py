"""
@file       2.1_External_Pull_Down.py
@brief      Reads a button on a pin held LOW by a 10 kOhm pull-down resistor to GND.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin
import time

BUTTON_PIN = 21
LED_PIN = 38

led = Pin(LED_PIN, Pin.OUT)

# Same resistor, other end of the circuit. Nothing about the button changed: the resistor decides the
# resting state, not the button.
button = Pin(BUTTON_PIN, Pin.IN)
print("EXTERNAL PULL-DOWN: LOW at rest, HIGH while pressed. The logic is inverted.")

while True:
    # Read the pin, show the reading on the LED and print it, then wait a moment.
    reading = button.value()

    led.value(reading)
    print(reading)

    time.sleep_ms(20)
