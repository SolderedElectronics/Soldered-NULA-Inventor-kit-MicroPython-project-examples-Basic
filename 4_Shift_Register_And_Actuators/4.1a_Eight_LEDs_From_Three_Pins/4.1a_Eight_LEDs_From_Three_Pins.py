"""
@file       4.1a_Eight_LEDs_From_Three_Pins.py
@brief      Drives eight LEDs from a 74HC595, times two different ways of getting a byte into it, and then
            walks a single lit bit across the row.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, SPI
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

# How many times each of the two ways sends the byte while it is being timed.
TIMING_UPDATES = 2000

latch = Pin(LATCH_PIN, Pin.OUT, value=0)
data = Pin(DATA_PIN, Pin.OUT)
clock = Pin(CLOCK_PIN, Pin.OUT)

# Output enable is active low, so holding it LOW is what makes the LEDs visible.
Pin(OE_PIN, Pin.OUT, value=0)

print()
print("74HC595 on IO11 (data), IO12 (clock), IO10 (latch), IO13 (output enable)")

# Same circuit, same result, two ways of sending the byte, and the gap between them is large. How you talk to a
# part is a design decision with a number attached, and in MicroPython the gap is wider than it is in C because
# every manual pin write goes through the interpreter. Both ways send the same byte, 0b10101010, and each one is
# repeated TIMING_UPDATES times while the clock runs.
print()

# Way 1, by hand. A shift register is a row of eight memory cells: put a bit on the data pin, pulse the clock, and
# every cell hands its contents to the next while the first takes the new bit. Eight bits means eight of those
# steps, written out here from the first bit to the last: 1, 0, 1, 0 and so on.
#
# Nothing appears on the outputs while this happens. They are fed from a second set of latches that only copy the
# row when the latch pin is pulsed, which is the last two lines.
start = time.ticks_us()
for i in range(TIMING_UPDATES):
    data.value(1)
    clock.value(1)
    clock.value(0)

    data.value(0)
    clock.value(1)
    clock.value(0)

    data.value(1)
    clock.value(1)
    clock.value(0)

    data.value(0)
    clock.value(1)
    clock.value(0)

    data.value(1)
    clock.value(1)
    clock.value(0)

    data.value(0)
    clock.value(1)
    clock.value(0)

    data.value(1)
    clock.value(1)
    clock.value(0)

    data.value(0)
    clock.value(1)
    clock.value(0)

    latch.value(1)
    latch.value(0)
elapsed = time.ticks_diff(time.ticks_us(), start)
updates_per_second = int(TIMING_UPDATES * 1000000.0 / elapsed)

print("manual pin writes: {} updates per second".format(updates_per_second))

# Way 2, with hardware SPI. The chip's hardware generates the clock, so the processor hands over one byte and is
# free until it is done. MicroPython has no shiftOut(), so these two are the whole choice.
#
# This has to come second. Handing the pins to the peripheral means a plain Pin write to either does nothing
# afterwards, and there is no way back inside one run.
spi = SPI(1, baudrate=8000000, polarity=0, phase=0, sck=Pin(CLOCK_PIN), mosi=Pin(DATA_PIN))

start = time.ticks_us()
for i in range(TIMING_UPDATES):
    spi.write(bytes([0b10101010]))

    latch.value(1)
    latch.value(0)
elapsed = time.ticks_diff(time.ticks_us(), start)
updates_per_second = int(TIMING_UPDATES * 1000000.0 / elapsed)

print("hardware SPI:      {} updates per second".format(updates_per_second))
print()

# Clock one lit bit along the row slowly enough to follow with your eye. The timing run handed the data and clock
# pins to the SPI peripheral, so the walk sends its bytes with SPI from here on. The LEDs cannot tell the
# difference.
#
# Each byte has a single bit set: 1 is 0b00000001, 2 is 0b00000010, 4 is 0b00000100 and so on up to 128. The last
# bit sent lands on QA, so QA is the least significant bit and QH the most significant.
while True:
    spi.write(bytes([1]))
    latch.value(1)
    latch.value(0)
    time.sleep_ms(150)

    spi.write(bytes([2]))
    latch.value(1)
    latch.value(0)
    time.sleep_ms(150)

    spi.write(bytes([4]))
    latch.value(1)
    latch.value(0)
    time.sleep_ms(150)

    spi.write(bytes([8]))
    latch.value(1)
    latch.value(0)
    time.sleep_ms(150)

    spi.write(bytes([16]))
    latch.value(1)
    latch.value(0)
    time.sleep_ms(150)

    spi.write(bytes([32]))
    latch.value(1)
    latch.value(0)
    time.sleep_ms(150)

    spi.write(bytes([64]))
    latch.value(1)
    latch.value(0)
    time.sleep_ms(150)

    spi.write(bytes([128]))
    latch.value(1)
    latch.value(0)
    time.sleep_ms(150)
