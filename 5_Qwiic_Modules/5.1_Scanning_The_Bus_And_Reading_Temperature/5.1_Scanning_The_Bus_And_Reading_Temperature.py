"""
@file       5.1_Scanning_The_Bus_And_Reading_Temperature.py
@brief      Finds out what is really on the I2C bus, then reads temperature from the TMP117 continuously and
            checks every reading is a real one.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, I2C
import time

# The Soldered driver for the TMP117, found in the lib folder of this repository. Copy the whole lib folder onto
# the board before running this.
from tmp117 import TMP117

# The Qwiic bus is IO8 (SDA) and IO9 (SCL) on this board. A module is reached by its address rather than by a pin,
# which is why several of them share one cable.
SDA_PIN = 8
SCL_PIN = 9

TMP117_ADDRESS = 0x49

"""
  MODE_SCAN  list every address that answers. Pull the Qwiic cable while it runs and watch the list shrink.
  MODE_READ  read temperature twice a second, checking each reading before printing it.
"""
MODE_SCAN = 0
MODE_READ = 1

MODE = MODE_SCAN

i2c = I2C(0, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN))

# The address is passed in because JP2 on the breakout ties ADD0 high, putting the sensor at 0x49.
tmp = TMP117(i2c, TMP117_ADDRESS)

if MODE == MODE_READ:
    # Continuous conversion, with a new-data callback or None for none.
    tmp.init(None)

print()


def scan_bus():
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


def read_temperature():
    """
    Pull the Qwiic cable out while this runs. In MicroPython the read raises OSError rather than quietly returning a
    number, which is the opposite of what the Arduino version of this example has to warn about: there, a missing
    sensor reads 0.0000 degrees and nothing looks wrong.

    Catching the error is not the whole job. A cable that is half out, or a second device answering at the same
    address, can still give you a number that arrived cleanly and means nothing. The TMP117's device ID register
    always reads 0x117, so ask for that as well.
    """
    try:
        celsius = tmp.getTemperature()
        device_id = tmp.getDeviceID()
    except OSError as e:
        print("no answer from the bus: {}. Check the Qwiic cable.".format(e))
        time.sleep_ms(500)
        return

    if device_id != 0x117:
        print("{:.4f} C   <-- device ID reads 0x{:X}, not 0x117. This number is meaningless.".format(
            celsius, device_id))
    else:
        print("{:.4f} C".format(celsius))

    time.sleep_ms(500)


while True:
    if MODE == MODE_SCAN:
        scan_bus()
    else:
        read_temperature()

"""
setAveraging() is deliberately left alone here. The sensor reports in steps of 0.0078 C and already sits near that
step with no averaging, so there is little noise to remove, while 64 samples stretches one reading to most of a
second. Averaging earns its keep on a noisy input, which is what the ADC in 2.2 was.

For 6.2: a Qwiic cable carries 3V3, GND, SDA and SCL and nothing else. The TMP117's alert output is not among them,
so that example reads the alert flag over the bus instead of wiring it.
"""
