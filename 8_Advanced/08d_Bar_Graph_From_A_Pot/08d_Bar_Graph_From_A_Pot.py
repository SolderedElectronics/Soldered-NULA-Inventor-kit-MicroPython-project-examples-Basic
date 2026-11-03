"""
@file       08d_Bar_Graph_From_A_Pot.py
@brief      Fills the row of eight LEDs on a 74HC595 one at a time as the pot is turned, like a bar graph.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, ADC
import time

"""
Find pin 1 first. It is at the end with the half-moon notch, left-hand pin with the notch at the top. Some packages
also carry a round dimple that is not next to the notch and is not pin 1 on this part.

Two things here are not optional and neither announces itself when missing. SRCLR must be held at 3V3 or the
register clears itself at random. And the 100 nF must sit as close to the chip's supply pins as the breadboard
allows, because eight outputs switching at once is a current spike the supply cannot follow.

Each of the eight outputs needs its own 330 Ohm resistor in series with its LED.
"""
DATA_PIN = 11
CLOCK_PIN = 12
LATCH_PIN = 10
OE_PIN = 13
POT_PIN = 4

latch = Pin(LATCH_PIN, Pin.OUT, value=0)
data = Pin(DATA_PIN, Pin.OUT)
clock = Pin(CLOCK_PIN, Pin.OUT)
pot = ADC(Pin(POT_PIN), atten=ADC.ATTN_11DB)

# Output enable is active low, so holding it LOW is what makes the LEDs visible.
Pin(OE_PIN, Pin.OUT, value=0)


def write_manual(value):
    """
    The manual version, one pin write at a time. A shift register is a row of eight memory cells: put a bit on the
    data pin, pulse the clock, and every cell hands its contents to the next while the first takes the new bit.

    Nothing appears on the outputs while this happens. They are fed from a second set of latches that only copy the
    row when the latch pin is pulsed.
    """
    for bit in range(7, -1, -1):
        data.value((value >> bit) & 1)
        clock.value(1)
        clock.value(0)

    latch.value(1)
    latch.value(0)


"""
A bar graph. The whole display is still one byte, so lighting five LEDs costs what lighting one costs.

Two habits from earlier are doing the work, and without them the LED at the boundary flickers: the EMA from T11
smooths the reading, and the hysteresis from T15 means a step only changes once the smoothed value has moved
clear of the edge by BAR_MARGIN counts.
"""
BAR_STEP = 4096 // 9  # nine states, from no LEDs lit to all eight
BAR_MARGIN = 40       # how far past an edge the pot has to go before the bar changes

pot_ema = -1.0
bar_level = 0

while True:
    raw = pot.read()

    # Seed the average on the first pass, or the bar crawls up from zero every time the board resets.
    if pot_ema < 0:
        pot_ema = raw
    # Faster than T11's 0.05, because a display the reader is turning has to keep up with their hand.
    pot_ema += 0.2 * (raw - pot_ema)

    if bar_level < 8 and pot_ema > (bar_level + 1) * BAR_STEP + BAR_MARGIN:
        bar_level += 1
    elif bar_level > 0 and pot_ema < bar_level * BAR_STEP - BAR_MARGIN:
        bar_level -= 1

    # One shift left, minus one, turns a count into a run of lit bits: 3 becomes 0b00000111.
    write_manual((1 << bar_level) - 1)

    time.sleep_ms(20)
