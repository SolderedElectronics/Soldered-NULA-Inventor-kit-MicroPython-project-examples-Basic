"""
@file       05f_Heartbeat.py
@brief      Makes the LED on IO38 beat like a heart: two quick pulses, then a rest. The potentiometer on IO4 sets
            the rate from 40 to 140 beats per minute, and the beat is drawn from a table of brightness values.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, ADC, PWM
import time

# The LED on IO38 needs a 330 Ohm resistor in series or it will be damaged. The pot's wiper is on IO4, as in T9.
LED_PIN = 38
POT_PIN = 4

# 5 kHz is far above what the eye can follow.
PWM_FREQ = 5000

# The slowest and fastest heartbeat the knob can ask for, in beats per minute.
MIN_BPM = 40
MAX_BPM = 140

# The BPM is printed only when it has moved at least this far from the last printed one.
PRINT_STEP_BPM = 5

# One whole beat drawn as 32 brightness values, from the start of the beat to the start of the next.
# Entries 0 to 7 are the first pulse (lub), 8 to 16 the second, smaller one (dub), and the rest is silence.
# The shape is the same at every speed. Only the time each entry lasts changes.
BEAT_SHAPE = (
    60, 160, 255, 200, 120, 50, 15, 5,
    0, 0, 40, 130, 190, 140, 70, 20,
    4, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,
)
BEAT_STEPS = len(BEAT_SHAPE)

# The same 12-bit, 3.3 V range as the other analog examples.
pot = ADC(Pin(POT_PIN), atten=ADC.ATTN_11DB)
led = PWM(Pin(LED_PIN), freq=PWM_FREQ, duty_u16=0)

# How long the beat in progress lasts, and when it started. Both are in milliseconds.
beat_ms = 1000
beat_start_ms = 0

# The BPM last printed. It starts far from any real value, so the first BPM is always printed.
printed_bpm = -100


# Reads the knob and turns it into beats per minute, from MIN_BPM at the left end to MAX_BPM at the right end.
def read_bpm():
    raw = pot.read()
    return MIN_BPM + (raw * (MAX_BPM - MIN_BPM)) // 4095


# Starts a new beat: reads the knob, works out how long one beat lasts at that rate, and prints the BPM if it
# has changed enough.
def start_beat(now):
    global beat_ms, beat_start_ms, printed_bpm

    bpm = read_bpm()

    # 60000 ms in a minute, divided by the beats in that minute, is the length of one beat.
    beat_ms = 60000 // bpm
    beat_start_ms = now

    if abs(bpm - printed_bpm) >= PRINT_STEP_BPM:
        printed_bpm = bpm
        print("BPM", bpm)


print("HEARTBEAT: the knob on IO4 sets 40 to 140 beats per minute.")

# The first beat starts now.
start_beat(time.ticks_ms())

while True:
    now = time.ticks_ms()
    elapsed_ms = time.ticks_diff(now, beat_start_ms)

    # When the beat is over, read the knob again and start the next one. The rate can change only here, once a beat.
    if elapsed_ms >= beat_ms:
        start_beat(now)
        elapsed_ms = 0

    # How far through the beat we are, turned into a position in the table. The result is 0 to 31.
    step = (elapsed_ms * BEAT_STEPS) // beat_ms

    # Show that entry of the table, scaled from 8 bits to MicroPython's 16-bit duty. There is no long sleep here:
    # the loop comes round every few milliseconds, so the clock decides which entry is showing, not a pause.
    led.duty_u16(BEAT_SHAPE[step] * 257)

    time.sleep_ms(5)
