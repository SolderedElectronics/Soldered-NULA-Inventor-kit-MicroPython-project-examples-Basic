"""
@file       03a_Button_Bounce.py
@brief      Samples a button every 50 us after a press and prints how long it rattles for.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin
import time

BUTTON_PIN = 21

# 50 us over 20 ms gives 400 readings, fine enough to see the individual make-and-break events of a contact.
BOUNCE_SAMPLES = 400
BOUNCE_INTERVAL_US = 50

# The pin is held HIGH by the pull-up inside the chip, so a press pulls it LOW.
button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
print("BOUNCE: press the button. The trace below is your button, sampled every 50 us.")

while True:
    # Arm only while the line is at rest. Pressed already means we have missed the edge.
    if button.value() == 0:
        continue

    # Spin until the contacts first touch. The bounce is over in a millisecond or two, so sampling has to
    # start at the edge, not after it.
    while button.value():
        pass

    # Take 400 readings, one every 50 us. Nothing else may happen in here, or the timing stops being true.
    trace = bytearray(BOUNCE_SAMPLES)
    next_us = time.ticks_us()

    for i in range(BOUNCE_SAMPLES):
        while time.ticks_diff(next_us, time.ticks_us()) > 0:
            pass
        trace[i] = 49 if button.value() else 48
        next_us = time.ticks_add(next_us, BOUNCE_INTERVAL_US)

    # The last sample that differs from the settled state is where the bounce ended.
    settled = trace[BOUNCE_SAMPLES - 1]
    last_different = -1
    for i in range(BOUNCE_SAMPLES):
        if trace[i] != settled:
            last_different = i

    bounce_ms = (last_different + 1) * BOUNCE_INTERVAL_US / 1000.0

    print()
    print(trace.decode())
    print("Bounce lasted about {:.2f} ms".format(bounce_ms))

    # Wait for release before arming again.
    while button.value() == 0:
        time.sleep_ms(10)
    time.sleep_ms(100)
