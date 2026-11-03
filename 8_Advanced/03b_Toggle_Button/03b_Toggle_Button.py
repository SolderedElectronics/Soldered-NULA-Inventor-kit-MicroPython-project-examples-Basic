"""
@file       03b_Toggle_Button.py
@brief      Toggles an LED on every clean press of a button, ignoring the contact bounce.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin
import time

BUTTON_PIN = 21
LED_PIN = 38

# A reading must stay the same for this long before the script believes it. Your own T9 result, rounded
# generously upwards, is the right number here. 30 ms covers almost every button.
DEBOUNCE_MS = 30

led = Pin(LED_PIN, Pin.OUT)
button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)

# The most recent raw reading, the last one we accepted as real, and the moment the raw reading last changed.
last_reading = 1
stable_state = 1
last_change_ms = time.ticks_ms()

# Whether the LED is currently on.
led_on = False

print("TOGGLE: press the button to switch the LED on, press again to switch it off.")

while True:
    reading = button.value()

    # Any change, including every bounce, restarts the stopwatch.
    if reading != last_reading:
        last_reading = reading
        last_change_ms = time.ticks_ms()

    # Once the reading has held still for DEBOUNCE_MS and differs from the state we accepted last,
    # it is a real change.
    if time.ticks_diff(time.ticks_ms(), last_change_ms) >= DEBOUNCE_MS and reading != stable_state:
        stable_state = reading

        # The pull-up makes a press read 0. Only the moment of pressing toggles the LED, not the release.
        if stable_state == 0:
            led_on = not led_on
            led.value(led_on)
            print("LED on" if led_on else "LED off")
