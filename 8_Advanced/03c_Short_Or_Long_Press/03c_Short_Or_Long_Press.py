"""
@file       03c_Short_Or_Long_Press.py
@brief      Measures how long a button is held and blinks the LED once or three times to match.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin
import time

BUTTON_PIN = 21
LED_PIN = 38

# A press held for at least this long counts as a long press.
LONG_PRESS_MS = 500

# Ignore changes that come sooner than this after the last one, so the contact bounce is not counted.
DEBOUNCE_MS = 30

led = Pin(LED_PIN, Pin.OUT)
button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)

was_pressed = False
pressed_at_ms = 0
last_edge_ms = time.ticks_ms()


# Blinks the LED a number of times, 150 ms on and 150 ms off each.
def blink_led(times):
    for i in range(times):
        led.value(1)
        time.sleep_ms(150)
        led.value(0)
        time.sleep_ms(150)


print("PRESS LENGTH: tap the button for one blink, hold it for three.")

while True:
    # The pull-up makes a press read 0, so a pressed button gives True here.
    pressed = (button.value() == 0)

    if pressed != was_pressed and time.ticks_diff(time.ticks_ms(), last_edge_ms) >= DEBOUNCE_MS:
        was_pressed = pressed
        last_edge_ms = time.ticks_ms()

        if pressed:
            # The button has just gone down: note the time and light the LED while it stays down.
            pressed_at_ms = time.ticks_ms()
            led.value(1)
        else:
            # The button has just come up: work out how long it was held.
            held_ms = time.ticks_diff(time.ticks_ms(), pressed_at_ms)
            led.value(0)

            print("Held for", held_ms, "ms")

            blink_led(3 if held_ms >= LONG_PRESS_MS else 1)
