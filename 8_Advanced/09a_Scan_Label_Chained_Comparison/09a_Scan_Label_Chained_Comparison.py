"""
@file       09a_Scan_Label_Chained_Comparison.py
@brief      Scans the I2C bus and prints every address that answers, so you can see what is really connected.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, I2C
import time

# The Qwiic bus is IO8 (SDA) and IO9 (SCL) on this board. A module is reached by its address rather than by a pin,
# which is why several of them share one cable.
SDA_PIN = 8
SCL_PIN = 9

TMP117_ADDRESS = 0x49

i2c = I2C(0, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN))

print()

while True:
    """
    Every I2C exchange starts with the controller calling out an address, and a device that recognises it answers
    with one acknowledge bit. i2c.scan() calls out all of them in turn and returns the ones that answered, which is
    the first thing to reach for when a Qwiic project stops working.

    Two addresses answer here and only one is yours: 0x51 is the real-time clock on the board itself. Pull the
    Qwiic cable while the scan runs and 0x49 disappears from the next block while 0x51 stays.
    """
    print("scanning I2C bus...")

    found = i2c.scan()

    for address in found:
        label = ""
        if address == TMP117_ADDRESS:
            label = "  TMP117"
        elif 0x30 <= address <= 0x37:
            label = "  relay"
        elif address == 0x51:
            label = "  onboard RTC, part of the board"
        print("  0x{:02X}{}".format(address, label))

    if not found:
        print("  nothing answered. Check the cable and that a module is plugged in.")

    print()
    time.sleep_ms(3000)
