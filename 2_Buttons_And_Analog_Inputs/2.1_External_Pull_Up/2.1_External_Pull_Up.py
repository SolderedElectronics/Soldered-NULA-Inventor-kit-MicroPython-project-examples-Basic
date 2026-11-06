"""
@file       2.1_External_Pull_Up.py
@brief      Reads a button on a pin held HIGH by a 10 kOhm pull-up resistor to 3V3.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin
import time

BUTTON_PIN = 21
LED_PIN = 38

led = Pin(LED_PIN, Pin.OUT)

# The 10 kOhm to 3V3 holds the pin HIGH; pressing connects it straight to GND, which wins. The resistor is
# what stops that being a short circuit between 3V3 and GND while the button is held.
button = Pin(BUTTON_PIN, Pin.IN)
print("EXTERNAL PULL-UP: HIGH at rest, LOW while pressed.")

while True:
    # Read the pin, show the reading on the LED and print it, then wait a moment.
    reading = button.value()

    led.value(reading)
    print(reading)

    time.sleep_ms(20)
