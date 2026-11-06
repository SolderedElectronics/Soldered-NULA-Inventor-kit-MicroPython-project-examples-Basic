"""
@file       2.1_Floating_Button.py
@brief      Reads a button on a pin that nothing is holding, so the reading drifts.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin
import time

BUTTON_PIN = 21
LED_PIN = 38

led = Pin(LED_PIN, Pin.OUT)

# Nothing is holding this pin anywhere, so it drifts and follows your hand. A pin with nothing attached
# does not read LOW, it reads whatever it feels like.
button = Pin(BUTTON_PIN, Pin.IN)
print("FLOATING: nothing is holding the pin. Move your hand near the wire.")

while True:
    # Read the pin, show the reading on the LED and print it, then wait a moment.
    reading = button.value()

    led.value(reading)
    print(reading)

    time.sleep_ms(20)
