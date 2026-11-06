"""
@file       2.1_Internal_Pull_Up.py
@brief      Reads a button using the pull-up resistor that is built into the chip.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin
import time

BUTTON_PIN = 21
LED_PIN = 38

led = Pin(LED_PIN, Pin.OUT)

# The same pull-up, moved inside the chip. It is around 45 kOhm, weak next to a 10 kOhm, so over a long
# wire it is slow to bring the line back up and easy for nearby noise to disturb.
button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
print("INTERNAL PULL-UP: no resistor on the board. Same readings as the external one.")

while True:
    # Read the pin, show the reading on the LED and print it, then wait a moment.
    reading = button.value()

    led.value(reading)
    print(reading)

    time.sleep_ms(20)
