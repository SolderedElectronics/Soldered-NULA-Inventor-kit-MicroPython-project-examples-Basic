"""
@file       10e_Sleep_Schedule.py
@brief      Wakes every ten seconds, reads the TMP117, and stores the reading in a ring of ten slots in RTC memory. On
            every tenth wake it prints the whole log, one line per slot, and then goes back to sleep.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, I2C, RTC, deepsleep
import machine
import struct
import time

# The Soldered driver for the TMP117, found in the lib folder of this repository.
from tmp117 import TMP117

# The LED is on IO38 and the TMP117 is on the Qwiic cable.
LED_PIN = 38
SDA_PIN = 8
SCL_PIN = 9
TMP117_ADDRESS = 0x49

# How long the board sleeps between two readings, in seconds.
SLEEP_SECONDS = 10

# The log holds this many readings. The script prints it every time this many wakes have gone by.
RING_SIZE = 10

# RTC memory holds bytes, not variables, so the wake count and the ten readings are packed into one block of bytes.
# "<I10h" means: one unsigned 32-bit number (the wake count), then ten signed 16-bit numbers (the readings), with no
# padding between them. Each reading is stored in hundredths of a degree, so 23.41 C is saved as 2341.
LOG_FORMAT = "<I10h"
LOG_SIZE = struct.calcsize(LOG_FORMAT)

led = Pin(LED_PIN, Pin.OUT)
i2c = I2C(0, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN))
tmp = TMP117(i2c, TMP117_ADDRESS)
rtc_mem = RTC()

# After a power-on or a reset the memory is not trusted, so the script starts with an empty log.
wake_count = 0
ring = [0] * RING_SIZE
saved = rtc_mem.memory()
if machine.reset_cause() == machine.DEEPSLEEP_RESET and len(saved) == LOG_SIZE:
    values = struct.unpack(LOG_FORMAT, saved)
    wake_count = values[0]
    ring = list(values[1:])


def blink(times):
    """Blinks the LED the given number of times."""
    for _ in range(times):
        led.value(1)
        time.sleep_ms(120)
        led.value(0)
        time.sleep_ms(120)


def print_log():
    """Prints the whole ring, oldest reading first. The slot after the newest one holds the oldest reading, and the
    remainder (%) makes the count wrap round from the last slot back to the first."""
    print("log of the last {} wakes:".format(RING_SIZE))

    for i in range(RING_SIZE):
        slot = (wake_count + i) % RING_SIZE
        wake_number = wake_count - RING_SIZE + 1 + i
        print("  wake {}  {:.2f} C".format(wake_number, ring[slot] / 100))


def sleep_again():
    """Saves the log into RTC memory and stops the board for SLEEP_SECONDS. The script starts again from its first
    line when the timer runs out."""
    rtc_mem.memory(struct.pack(LOG_FORMAT, wake_count, *ring))
    deepsleep(SLEEP_SECONDS * 1000)


first_boot = (wake_count == 0)
if first_boot:
    time.sleep_ms(1000)

# The sensor keeps its settings through sleep, so it is configured only once. The wait gives it time to finish its
# first one-second conversion.
if first_boot:
    tmp.init(None)
    time.sleep_ms(1100)

    print()
    print("sleep schedule: one reading every 10 s, the log prints on every tenth wake")

# MicroPython raises an error when nothing answers, and the device ID catches the case where something answers but is
# not a TMP117. A failed wake is not counted and nothing is stored.
try:
    device_id = tmp.getDeviceID()
    celsius = tmp.getTemperature()
except (OSError, IndexError):
    print("no answer from the bus. Check the Qwiic cable.")
    blink(5)
    sleep_again()

if device_id != 0x117:
    print("no TMP117 on the bus. Check the Qwiic cable.")
    blink(5)
    sleep_again()

# Wake number n goes into slot n - 1, and the remainder wraps the slot number round after the last one. The reading
# is stored in hundredths of a degree as a whole number.
slot = wake_count % RING_SIZE
ring[slot] = round(celsius * 100)
wake_count += 1

print("wake {}: {:.2f} C, stored in slot {}".format(wake_count, ring[slot] / 100, slot + 1))

# Every tenth wake, print the log and blink twice. Every other wake blinks once.
if wake_count % RING_SIZE == 0:
    print_log()
    blink(2)
else:
    blink(1)

sleep_again()
