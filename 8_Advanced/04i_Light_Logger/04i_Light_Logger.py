"""
@file       04i_Light_Logger.py
@brief      Reads the photoresistor on IO4 twice a second into a ring buffer that holds the last minute, and once
            a second prints the latest reading with the minimum, maximum and average over the whole buffer.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, ADC
import time

# The middle of the photoresistor divider, same pin as T9 and T10 used.
LDR_PIN = 4

# One reading every 500 ms, and one line printed every 1000 ms.
READ_INTERVAL_MS = 500
PRINT_INTERVAL_MS = 1000

# The buffer holds 120 readings, which at two a second is exactly one minute.
BUFFER_SIZE = 120

# The same 12-bit, 3.3 V range as the other analog examples.
ldr = ADC(Pin(LDR_PIN), atten=ADC.ATTN_11DB)

# The ring buffer: a fixed row of slots that the newest reading keeps overwriting the oldest one in.
readings = [0] * BUFFER_SIZE

# The slot the next reading goes into, how many slots hold a reading so far, and the sum of all those readings.
next_slot = 0
reading_count = 0
running_sum = 0

# The most recent reading.
latest_reading = 0


# Puts a new reading into the buffer. Once the buffer is full, the slot being overwritten holds the oldest reading,
# so that value is taken off the running sum before the new one is added. The average never needs a loop.
def add_reading(value):
    global next_slot, reading_count, running_sum, latest_reading

    if reading_count == BUFFER_SIZE:
        running_sum = running_sum - readings[next_slot]

    readings[next_slot] = value
    running_sum = running_sum + value
    latest_reading = value

    # Move on to the next slot, and go back to the first one after the last.
    next_slot = (next_slot + 1) % BUFFER_SIZE

    # Count the slots in use, until they are all in use.
    if reading_count < BUFFER_SIZE:
        reading_count = reading_count + 1


# Prints the latest reading with the minimum, maximum and average of everything in the buffer.
def print_summary():
    # The minimum and maximum have to look at every reading in use. Slots are filled from 0 upwards, so
    # until the buffer is full the readings are in slots 0 to reading_count - 1.
    used = readings[:reading_count]
    lowest = min(used)
    highest = max(used)

    # The average comes straight from the running sum.
    average = running_sum / reading_count

    print("Now %d, min %d, max %d, average %.1f (%d readings)" % (latest_reading, lowest, highest, average, reading_count))


print("LIGHT LOGGER: one reading every 500 ms, the last 120 (one minute) kept.")

# Take the first reading straight away, so the buffer is never empty when the first line is printed.
add_reading(ldr.read())
last_read_ms = time.ticks_ms()
last_print_ms = time.ticks_ms()

while True:
    now = time.ticks_ms()

    # Every 500 ms, take a reading and put it in the buffer.
    if time.ticks_diff(now, last_read_ms) >= READ_INTERVAL_MS:
        last_read_ms = now
        add_reading(ldr.read())

    # Every second, print the summary.
    if time.ticks_diff(now, last_print_ms) >= PRINT_INTERVAL_MS:
        last_print_ms = now
        print_summary()

    time.sleep_ms(10)
