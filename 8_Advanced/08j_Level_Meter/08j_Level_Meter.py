"""
@file       08j_Level_Meter.py
@brief      An eight-LED level meter on a 74HC595. The number of lit LEDs follows the pot, and one more LED marks
            the highest level reached, falling one step every second. The register is written only when the
            pattern changes.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, ADC
import time

"""
Find pin 1 first. It is at the end with the half-moon notch, left-hand pin with the notch at the top. Some packages
also carry a round dimple that is not next to the notch and is not pin 1 on this part.

SRCLR must be held at 3V3 or the register clears itself at random, and the 100 nF must sit as close to the chip's
supply pins as the breadboard allows.
"""
DATA_PIN = 11
CLOCK_PIN = 12
LATCH_PIN = 10
OE_PIN = 13
POT_PIN = 4

# Smooths the pot reading. It is faster than T13's 0.05, because a meter has to keep up with your hand.
EMA_ALPHA = 0.2

# The peak stays for this long before it falls one step.
PEAK_FALL_MS = 1000

latch = Pin(LATCH_PIN, Pin.OUT, value=0)
data = Pin(DATA_PIN, Pin.OUT)
clock = Pin(CLOCK_PIN, Pin.OUT)
pot = ADC(Pin(POT_PIN), atten=ADC.ATTN_11DB)

# Output enable is active low, so holding it LOW is what makes the LEDs visible.
Pin(OE_PIN, Pin.OUT, value=0)


def build_pattern(bar_level, peak_level):
    """Build the byte for the register: a run of lit LEDs for the level, plus one more LED for the peak."""
    # One shift left, minus one, turns a count into a run of lit bits: 3 becomes 0b00000111.
    bar = (1 << bar_level) - 1

    # The peak is a single lit bit, at the position of the highest level reached. No peak means no bit.
    peak_bit = 0
    if peak_level > 0:
        peak_bit = 1 << (peak_level - 1)

    # OR keeps every bit that is set in either, so the bar and the peak LED both stay lit.
    return bar | peak_bit


def write_manual(value):
    """Send one byte to the register, one pin write at a time. Nothing appears on the outputs until the latch is
    pulsed."""
    for bit in range(7, -1, -1):
        data.value((value >> bit) & 1)
        clock.value(1)
        clock.value(0)

    latch.value(1)
    latch.value(0)


# The current level and the peak, both from 0 (nothing lit) to 8 (every LED lit).
level = 0
peak = 0
last_peak_move_ms = time.ticks_ms()

# The first reading starts the average, or the bar crawls up from zero every time the board resets.
pot_ema = float(pot.read())

# What was last shown and printed. -1 is a value nothing can have, so the first pass always writes and prints.
last_pattern = -1
last_level = -1
last_peak = -1

print("LEVEL: the bar follows the knob and the peak falls one step a second.")

while True:
    pot_ema += EMA_ALPHA * (pot.read() - pot_ema)

    # Nine states, from 0 to 8 LEDs lit. The largest reading, 4095, gives 8.
    level = min(8, max(0, int(pot_ema * 9 / 4096)))

    # Raise the peak at once when the level reaches it, and let it fall one step for every PEAK_FALL_MS the level
    # has stayed below it.
    if level >= peak:
        peak = level
        last_peak_move_ms = time.ticks_ms()
    elif time.ticks_diff(time.ticks_ms(), last_peak_move_ms) >= PEAK_FALL_MS:
        peak -= 1
        last_peak_move_ms = time.ticks_ms()

    # Write the register only when the pattern is not the one already showing.
    pattern = build_pattern(level, peak)
    if pattern != last_pattern:
        write_manual(pattern)
        last_pattern = pattern

    # Print only when the level or the peak changed.
    if level != last_level or peak != last_peak:
        last_level = level
        last_peak = peak
        print("level {} peak {}".format(level, peak))

    time.sleep_ms(20)
