"""
@file       2.1_Pull_Up_Resistors_And_Button_Debouncing.py
@brief      One button read five ways: floating, external pull-up, external pull-down, internal pull-up, and a
            capture of the bounce itself. The code barely changes; the circuit does.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Soldered Electronics
"""

from machine import Pin
import time

"""
Work through the modes in order. The code barely changes between them. What changes is the circuit, and that is the
point of the page, so each mode needs its own wiring before you run it.

  MODE_FLOATING     no resistor holding the pin at all. Reads whatever is nearby.
  MODE_PULLUP_EXT   a resistor to 3V3 holds the pin HIGH at rest, so a press reads LOW.
  MODE_PULLDOWN_EXT a resistor to GND holds it LOW at rest, so the readings come out inverted.
  MODE_PULLUP_INT   the same pull-up, provided inside the chip instead of on the breadboard.
  MODE_BOUNCE       samples IO21 every 50 us and prints how long your button rattles for.
"""
MODE_FLOATING = 0
MODE_PULLUP_EXT = 1
MODE_PULLDOWN_EXT = 2
MODE_PULLUP_INT = 3
MODE_BOUNCE = 4

MODE = MODE_FLOATING

BUTTON_PIN = 21
LED_PIN = 38

# 50 us over 20 ms gives 400 readings, fine enough to see the individual make-and-break events of a contact.
BOUNCE_SAMPLES = 400
BOUNCE_INTERVAL_US = 50

led = Pin(LED_PIN, Pin.OUT)

if MODE == MODE_FLOATING:
    # Nothing is holding this pin anywhere, so it drifts and follows your hand. A pin with nothing attached
    # does not read LOW, it reads whatever it feels like.
    button = Pin(BUTTON_PIN, Pin.IN)
    print("FLOATING: nothing is holding the pin. Move your hand near the wire.")

elif MODE == MODE_PULLUP_EXT:
    # The 10 kOhm to 3V3 holds the pin HIGH; pressing connects it straight to GND, which wins. The resistor is
    # what stops that being a short circuit between 3V3 and GND while the button is held.
    button = Pin(BUTTON_PIN, Pin.IN)
    print("EXTERNAL PULL-UP: HIGH at rest, LOW while pressed.")

elif MODE == MODE_PULLDOWN_EXT:
    # Same resistor, other end of the circuit. Nothing about the button changed: the resistor decides the
    # resting state, not the button.
    button = Pin(BUTTON_PIN, Pin.IN)
    print("EXTERNAL PULL-DOWN: LOW at rest, HIGH while pressed. The logic is inverted.")

else:
    # The same pull-up, moved inside the chip. It is around 45 kOhm, weak next to a 10 kOhm, so over a long
    # wire it is slow to bring the line back up and easy for nearby noise to disturb.
    button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
    if MODE == MODE_PULLUP_INT:
        print("INTERNAL PULL-UP: no resistor on the board. Same readings as the external one.")
    else:
        print("BOUNCE: press the button. The trace below is your button, sampled every 50 us.")


def show_raw_reading():
    reading = button.value()

    led.value(reading)
    print(reading)

    time.sleep_ms(20)


def capture_bounce():
    """
    A pushbutton is two pieces of springy metal, and they meet and part several times in the first few milliseconds
    while the spring settles. The pin reads every one of those as a separate press. This waits for the first edge
    and then samples flat out, so the trace is your button rather than somebody else's.
    """
    # Arm only while the line is at rest. Pressed already means we have missed the edge.
    if button.value() == 0:
        return

    # Spin until the contacts first touch. Nothing else may happen in here: the bounce is
    # over in a millisecond or two, so sampling has to start at the edge, not after it.
    while button.value():
        pass

    trace = bytearray(BOUNCE_SAMPLES)
    next_us = time.ticks_us()

    for i in range(BOUNCE_SAMPLES):
        # Busy-wait until this sample is due. Nothing else may happen in here, or the timing stops being true.
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

    # Round that up generously and it is your debounce interval. Then ignore further changes for that long rather
    # than calling sleep, which stops everything else in the program too.

    # Wait for release before arming again.
    while button.value() == 0:
        time.sleep_ms(10)
    time.sleep_ms(100)


while True:
    if MODE == MODE_BOUNCE:
        capture_bounce()
    else:
        show_raw_reading()
