"""
@file       4.1_Eight_LEDs_From_Three_Pins.py
@brief      Drives eight LEDs from a 74HC595, times two different ways of getting a byte into it, adds hardware
            brightness control and a pot-driven bar graph, and then breaks the latch on purpose.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Soldered Electronics
"""

from machine import Pin, PWM, ADC, SPI
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

"""
  MODE_SPEED       times both ways of sending a byte, then walks a single bit across the LEDs
  MODE_BRIGHTNESS  a PWM signal on output-enable, with the pot setting the level
  MODE_BARGRAPH    the pot fills the row of LEDs one at a time, as a bar graph
  MODE_BROKEN      latching while shifting, so you can see what the latch is for
"""
MODE_SPEED = 0
MODE_BRIGHTNESS = 1
MODE_BARGRAPH = 2
MODE_BROKEN = 3

MODE = MODE_BRIGHTNESS

TIMING_UPDATES = 2000

latch = Pin(LATCH_PIN, Pin.OUT, value=0)
data = Pin(DATA_PIN, Pin.OUT)
clock = Pin(CLOCK_PIN, Pin.OUT)
pot = ADC(Pin(POT_PIN), atten=ADC.ATTN_11DB)

spi = None
oe_pwm = None

if MODE == MODE_BRIGHTNESS:
    oe_pwm = PWM(Pin(OE_PIN), freq=5000, duty_u16=0)
else:
    # Output enable is active low, so holding it LOW is what makes the LEDs visible in every other mode.
    Pin(OE_PIN, Pin.OUT, value=0)

print()
print("74HC595 on IO11 (data), IO12 (clock), IO10 (latch), IO13 (output enable)")


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


def write_spi(value):
    """The same signalling, except the chip's hardware generates the clock. The processor hands over one byte and is
    free until it is done. MicroPython has no shiftOut(), so these two are the whole choice."""
    spi.write(bytes([value]))

    latch.value(1)
    latch.value(0)


def measure(writer):
    start = time.ticks_us()
    for i in range(TIMING_UPDATES):
        writer(i & 0xFF)
    elapsed = time.ticks_diff(time.ticks_us(), start)

    return int(TIMING_UPDATES * 1000000.0 / elapsed)


def walk_one_bit(writer):
    """Clock one lit bit along the row slowly enough to follow with your eye. The last bit shifted lands on QA, so
    QA is the least significant bit and QH the most significant."""
    for i in range(8):
        writer(1 << i)
        time.sleep_ms(150)


if MODE == MODE_SPEED:
    # Same circuit, same result, two ways of getting there, and the gap between them is large. How you talk to a
    # part is a design decision with a number attached, and in MicroPython the gap is wider than it is in C because
    # every manual pin write goes through the interpreter.
    print()
    print("manual pin writes: {} updates per second".format(measure(write_manual)))

    # SPI must come second. Handing the pins to the peripheral means a plain Pin write to either does nothing
    # afterwards, and there is no way back inside one run.
    spi = SPI(1, baudrate=8000000, polarity=0, phase=0, sck=Pin(CLOCK_PIN), mosi=Pin(DATA_PIN))

    print("hardware SPI:      {} updates per second".format(measure(write_spi)))
    print()

    while True:
        # The timing run handed the data and clock pins to the SPI peripheral, so the walk has to use the SPI writer
        # from here on. The LEDs cannot tell the difference.
        walk_one_bit(write_spi)

elif MODE == MODE_BRIGHTNESS:
    # Output enable does not change what is in the register, it decides whether the outputs are connected at all.
    # Feed it PWM and all eight dim together for no processor time at all. The duty is inverted because the pin is
    # active low: full duty would hold the outputs off permanently.
    while True:
        # All eight on, so the dimming happens to the whole row and not to a pattern.
        write_manual(0b11111111)

        brightness = pot.read() * 16  # 0-4095 counts scaled to roughly 0-65535
        oe_pwm.duty_u16(65535 - min(65535, brightness))

        time.sleep_ms(20)

elif MODE == MODE_BARGRAPH:
    """
    A bar graph. The whole display is still one byte, so lighting five LEDs costs what lighting one costs.

    Two habits from earlier are doing the work, and without them the LED at the boundary flickers: the EMA from 2.2
    smooths the reading, and the hysteresis from 2.3 means a step only changes once the smoothed value has moved
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
        # Faster than 2.2's 0.05, because a display the reader is turning has to keep up with their hand.
        pot_ema += 0.2 * (raw - pot_ema)

        if bar_level < 8 and pot_ema > (bar_level + 1) * BAR_STEP + BAR_MARGIN:
            bar_level += 1
        elif bar_level > 0 and pot_ema < bar_level * BAR_STEP - BAR_MARGIN:
            bar_level -= 1

        # One shift left, minus one, turns a count into a run of lit bits: 3 becomes 0b00000111.
        write_manual((1 << bar_level) - 1)

        time.sleep_ms(20)

else:
    # The latch pulsed after every single bit instead of once at the end, so the outputs show the register mid-shift
    # eight times per byte. The LEDs blur and the pattern you asked for is never actually displayed.
    while True:
        value = 0b11110000

        for bit in range(7, -1, -1):
            data.value((value >> bit) & 1)
            clock.value(1)
            clock.value(0)

            # The mistake, on purpose.
            latch.value(1)
            latch.value(0)

            time.sleep_ms(120)

        time.sleep_ms(400)
