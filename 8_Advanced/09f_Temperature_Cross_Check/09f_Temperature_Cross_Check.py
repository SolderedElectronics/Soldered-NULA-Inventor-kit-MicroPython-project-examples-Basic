"""
@file       09f_Temperature_Cross_Check.py
@brief      Reads the room temperature from the TMP117 and the temperature of the ESP32-S3 chip itself every two
            seconds, prints both with their difference, and keeps a running mean of that difference.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, I2C
import esp32
import time

# The Soldered driver for the TMP117, found in the lib folder of the examples repository.
from tmp117 import TMP117

# The Qwiic bus is IO8 (SDA) and IO9 (SCL). The TMP117 is at the address from T22. The chip's own sensor needs no
# pin and no wire.
SDA_PIN = 8
SCL_PIN = 9
TMP117_ADDRESS = 0x49

# How long to wait between two readings, in milliseconds.
READ_INTERVAL_MS = 2000

i2c = I2C(0, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN))
tmp = TMP117(i2c, TMP117_ADDRESS)
tmp.init(None)

# The running mean of the difference is kept as a sum and a count, so no list of old readings is needed.
difference_sum = 0.0
difference_count = 0


def add_to_mean(difference):
    """Adds one difference to the running total and returns the mean of every difference so far."""
    global difference_sum, difference_count
    difference_sum = difference_sum + difference
    difference_count = difference_count + 1
    return difference_sum / difference_count


print()
print("room is the TMP117, chip is the ESP32-S3. Difference is chip minus room.")

while True:
    # Read both sources. MicroPython raises an error when the TMP117 does not answer at all, and the device ID
    # catches the case where something answers but is not a TMP117, as in T22.
    try:
        room_celsius = tmp.getTemperature()
        device_id = tmp.getDeviceID()
    except (OSError, IndexError):
        print("no answer from the bus. Check the Qwiic cable.")
        time.sleep_ms(READ_INTERVAL_MS)
        continue

    # A wrong ID means the room value is not a measurement. Such a reading is left out of the mean, or it would drag
    # the mean towards nonsense.
    if device_id != 0x117:
        print("device ID reads wrong, so the room value is not trusted. Check the Qwiic cable.")
        time.sleep_ms(READ_INTERVAL_MS)
        continue

    # esp32.mcu_temperature() is the sensor inside the chip and needs nothing connected.
    chip_celsius = esp32.mcu_temperature()

    # The difference is data. It tells you how far the chip sits above the room, not how wrong either source is.
    difference = chip_celsius - room_celsius
    mean_difference = add_to_mean(difference)

    # The + in the format makes the sign always print, so a positive difference shows a plus.
    print("room {:.2f} C  chip {:.2f} C  difference {:+.2f} C  mean {:+.2f} C".format(
        room_celsius, chip_celsius, difference, mean_difference))

    time.sleep_ms(READ_INTERVAL_MS)
