"""
@file       08e_Scanner.py
@brief      Runs a single lit LED back and forth along a row of eight LEDs on a 74HC595, with a pot setting the
            speed and output enable PWM setting the brightness.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, PWM, ADC
import time

# The same four control pins as T26 and T27, and the pot on IO4.
DATA_PIN = 11
CLOCK_PIN = 12
LATCH_PIN = 10
OE_PIN = 13
POT_PIN = 4

# How bright the lit LED is, as a percentage. A middle value is easy on the eyes.
BRIGHTNESS_PERCENT = 40

# The time the dot spends on each LED, in milliseconds. The knob picks a value between these two.
SLOWEST_MS = 400
FASTEST_MS = 40

latch = Pin(LATCH_PIN, Pin.OUT, value=0)
data = Pin(DATA_PIN, Pin.OUT)
clock = Pin(CLOCK_PIN, Pin.OUT)
pot = ADC(Pin(POT_PIN), atten=ADC.ATTN_11DB)

# Output enable is active low, so the duty is inverted: a bigger brightness means a smaller duty.
oe_pwm = PWM(Pin(OE_PIN), freq=5000, duty_u16=65535 - (BRIGHTNESS_PERCENT * 65535) // 100)


def write_manual(value):
    """Sends one byte to the 74HC595, most significant bit first, and then pulses the latch so all eight outputs
    change together."""
    for bit in range(7, -1, -1):
        data.value((value >> bit) & 1)
        clock.value(1)
        clock.value(0)

    latch.value(1)
    latch.value(0)


dot = 0         # which LED is lit, 0 to 7
direction = 1   # 1 means moving up the row, -1 means moving back down
last_step_ms = time.ticks_ms()

while True:
    # Turn the knob reading into the time to wait between steps. Knob down is slow, knob up is fast.
    step_ms = SLOWEST_MS - (pot.read() * (SLOWEST_MS - FASTEST_MS)) // 4095

    # Check the clock instead of sleeping for the whole step, so the knob is read many times per step and a change
    # is felt at once.
    if time.ticks_diff(time.ticks_ms(), last_step_ms) >= step_ms:
        last_step_ms = time.ticks_ms()

        # Show the dot where it is now, then work out where it goes next.
        write_manual(1 << dot)

        dot += direction
        if dot >= 7:
            direction = -1
        elif dot <= 0:
            direction = 1

    time.sleep_ms(2)
