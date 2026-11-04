"""
@file       02g_Knight_Rider_Fade.py
@brief      A bright spot that bounces along five LEDs on IO38 to IO42 and leaves a fading tail behind it.
            Each LED is dimmed with hardware PWM, using a table of brightness values by distance from the spot.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, PWM
import time

# The five LEDs, left to right as they sit on the breadboard, each with its own 330 Ohm resistor.
# 5 kHz is far above what the eye can follow. Every pin is handed to a hardware PWM channel, so the
# processor does not have to switch the LEDs itself.
LED_PINS = (38, 39, 40, 41, 42)
PWM_FREQ = 5000
leds = [PWM(Pin(p), freq=PWM_FREQ, duty_u16=0) for p in LED_PINS]
LED_COUNT = len(leds)

# How long the spot stays on each LED, in milliseconds.
STEP_MS = 100

# The brightness table. Entry 0 is the spot itself, entry 1 is the LED it just left, entry 2 the one before that.
# The values fall by about a third each time, because the eye sees small differences in a dim light more easily.
TAIL_BRIGHTNESS = (255, 90, 28, 6)
TAIL_LENGTH = len(TAIL_BRIGHTNESS)

# The LEDs the spot has visited, newest first. trail[0] is where the spot is now, trail[1] where it was one step ago.
trail = [0] * TAIL_LENGTH

# Which way the spot is heading: 1 is to the right, -1 is to the left.
direction = 1


# Writes a brightness to every LED. An LED takes the highest value the table gives for any step of the trail
# that sits on it, so an LED the spot has just crossed twice (at a turn) is not dimmed by the older visit.
def show_trail():
    for led in range(LED_COUNT):
        brightness = 0

        for step in range(TAIL_LENGTH):
            if trail[step] == led and TAIL_BRIGHTNESS[step] > brightness:
                brightness = TAIL_BRIGHTNESS[step]

        # MicroPython's duty is 16-bit, 0 to 65535, so an 8-bit table value is multiplied by 257 to cover the same range.
        leds[led].duty_u16(brightness * 257)


# Moves the spot one LED along, turning it round at either end, and shifts the old positions down the trail.
def move_spot():
    global direction

    # Every old position moves one place back in the trail. The oldest one drops off the end.
    for step in range(TAIL_LENGTH - 1, 0, -1):
        trail[step] = trail[step - 1]

    # Take one step in the current direction. If that would leave the row, turn round first.
    next_position = trail[0] + direction
    if next_position < 0 or next_position >= LED_COUNT:
        direction = -direction
        next_position = trail[0] + direction

    trail[0] = next_position


print("SCANNER: a bright spot with a fading tail bounces along the row.")

while True:
    # Show the spot and its tail, wait one step, then move the spot on.
    show_trail()
    time.sleep_ms(STEP_MS)
    move_spot()
