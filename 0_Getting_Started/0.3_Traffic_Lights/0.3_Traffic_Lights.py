"""
@file       0.3_Traffic_Lights.py
@brief      One LED, two LEDs alternating, a running light, a car light and a pedestrian crossing, in five modes
            idea each. Every mode uses the same five LEDs on the same five pins, so nothing gets rewired.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Soldered Electronics
"""

from machine import Pin
import time

"""
Work through the modes in order. Each one adds exactly one idea to the one before it.

  MODE_ONE          one LED blinking, the smallest program that does anything visible
  MODE_ALTERNATE    two LEDs taking turns, which is the same program with the second half inverted
  MODE_RUNNING      a lit spot walking along the row, the first program with a position to remember
  MODE_TRAFFIC      a car light cycling red, red-yellow, green, yellow
  MODE_CROSSING     the same light, plus a pedestrian light that is the opposite of it

All five LEDs need their own 330 Ohm resistor in series.
"""
MODE_ONE = 0
MODE_ALTERNATE = 1
MODE_RUNNING = 2
MODE_TRAFFIC = 3
MODE_CROSSING = 4

MODE = MODE_ALTERNATE

# Five LEDs on five pins, left to right as they sit on the breadboard. IO38 to IO42 are next to each other on the
# header, none of them has an analog input on it, and nothing on the board uses them.
LED_PINS = (38, 39, 40, 41, 42)

# Which of the five is which, for the traffic light modes. The car light uses the first three.
CAR_RED = 0
CAR_YELLOW = 1
CAR_GREEN = 2
PED_RED = 3
PED_GREEN = 4

# How long one step lasts, in milliseconds. Everything here is a multiple of it, so changing this one number
# changes the speed of every mode.
STEP_MS = 500

# Every one of the five pins is an output, whichever mode is selected.
leds = [Pin(p, Pin.OUT) for p in LED_PINS]
for led in leds:
    led.value(0)

# Where the lit spot currently is, in MODE_RUNNING. It has to survive from one pass of the loop to the next.
running_position = 0


def all_off():
    """Every LED dark."""
    for led in leds:
        led.value(0)


def set_car_light(red, yellow, green):
    """Set all three car lamps at once, so a combination that does not exist on a real road cannot be written."""
    leds[CAR_RED].value(red)
    leds[CAR_YELLOW].value(yellow)
    leds[CAR_GREEN].value(green)


def set_ped_light(red, green):
    """Set both pedestrian lamps at once, for the same reason."""
    leds[PED_RED].value(red)
    leds[PED_GREEN].value(green)


def run_one():
    """One LED on, one LED off, forever. The smallest program in the manual that does something you can see."""
    leds[0].value(1)
    time.sleep_ms(STEP_MS)

    leds[0].value(0)
    time.sleep_ms(STEP_MS)


def run_alternate():
    """Two LEDs taking turns. The only new idea is that the second is always given the opposite of the first."""
    leds[0].value(1)
    leds[1].value(0)
    time.sleep_ms(STEP_MS)

    leds[0].value(0)
    leds[1].value(1)
    time.sleep_ms(STEP_MS)


def run_running():
    """
    A lit spot walking along the row. This is the first program that has to remember something between one step
    and the next: which LED is currently lit. That is what running_position is for.
    """
    global running_position

    # Everything off, so only the new position is lit and the old one does not have to be cleared by name.
    all_off()

    leds[running_position].value(1)
    time.sleep_ms(STEP_MS)

    # Step along, and wrap back to the start after the last LED.
    running_position = running_position + 1
    if running_position >= len(leds):
        running_position = 0


def run_traffic():
    """
    A car traffic light, the four-phase kind: red, red and yellow together, green, yellow, and round again. Each
    phase is a whole state of all three lamps rather than a change to one of them, which is what stops the light
    ever showing a combination that does not exist in real life.
    """
    set_car_light(1, 0, 0)  # red
    time.sleep_ms(STEP_MS * 4)

    set_car_light(1, 1, 0)  # red and yellow, get ready
    time.sleep_ms(STEP_MS * 2)

    set_car_light(0, 0, 1)  # green
    time.sleep_ms(STEP_MS * 4)

    set_car_light(0, 1, 0)  # yellow
    time.sleep_ms(STEP_MS * 2)


def run_crossing():
    """
    The same car light with a pedestrian light beside it. The pedestrian light is not a second sequence running on
    its own: it is set inside the same four phases, which is what guarantees the two can never both be green.
    """
    set_car_light(1, 0, 0)  # cars stopped
    set_ped_light(0, 1)  # so people may cross
    time.sleep_ms(STEP_MS * 4)

    set_car_light(1, 1, 0)  # cars getting ready
    set_ped_light(1, 0)  # people already stopped, so the crossing clears first
    time.sleep_ms(STEP_MS * 2)

    set_car_light(0, 0, 1)  # cars moving
    set_ped_light(1, 0)
    time.sleep_ms(STEP_MS * 4)

    set_car_light(0, 1, 0)  # cars slowing
    set_ped_light(1, 0)
    time.sleep_ms(STEP_MS * 2)


if MODE == MODE_ONE:
    print("ONE: the first LED blinks. Everything else stays dark.")
elif MODE == MODE_ALTERNATE:
    print("ALTERNATE: two LEDs take turns. One is always lit.")
elif MODE == MODE_RUNNING:
    print("RUNNING: a lit spot walks along the row and starts again.")
elif MODE == MODE_TRAFFIC:
    print("TRAFFIC: red, red and yellow, green, yellow, and round again.")
elif MODE == MODE_CROSSING:
    print("CROSSING: the same car light, with a pedestrian light that is its opposite.")

while True:
    if MODE == MODE_ONE:
        run_one()
    elif MODE == MODE_ALTERNATE:
        run_alternate()
    elif MODE == MODE_RUNNING:
        run_running()
    elif MODE == MODE_TRAFFIC:
        run_traffic()
    elif MODE == MODE_CROSSING:
        run_crossing()
