"""
@file       2.1_Button_Bounce.py
@brief      Samples a button every 50 us after a press and prints how long it rattles for.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin
import time

BUTTON_PIN = 21

# The pin is held HIGH by the pull-up inside the chip, so a press pulls it LOW.
button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
print("BOUNCE: press the button. The trace below is your button, sampled every 50 us.")

while True:
    # Arm only while the line is at rest. Pressed already means we have missed the edge.
    if button.value() == 0:
        continue

    # Wait for the line to go low, which is the moment the contacts first touch.
    while button.value():
        pass

    # 400 readings, one every 50 us, make 20 ms. That is fine enough to see each make-and-break of the contacts.
    # Start with a list of 400 zeros, then overwrite each slot with the real reading.
    trace = ["0"] * 400

    # Take the 400 readings and store each one as the character "1" or "0".
    # Nothing else may happen in here, not even a print, or the timing stops being true.
    for i in range(400):
        if button.value():
            trace[i] = "1"
        else:
            trace[i] = "0"
        time.sleep_us(50)

    # The last reading is where the button settled. Walk through the trace and remember the last place
    # that disagreed with it. That is where the bounce ended.
    settled = trace[399]
    last_different = -1
    for i in range(400):
        if trace[i] != settled:
            last_different = i

    # Each reading is 50 us, which is 0.05 ms.
    bounce_ms = (last_different + 1) * 0.05

    print()
    print("".join(trace))
    print("Bounce lasted about {:.2f} ms".format(bounce_ms))

    # Wait for release before arming again.
    while button.value() == 0:
        time.sleep_ms(10)
    time.sleep_ms(100)
