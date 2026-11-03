"""
@file       09e_Advanced_Find_The_Relay.py
@brief      Looks for the relay on the Qwiic bus instead of assuming its address, then switches it on and off
            slowly so you can hear it.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, I2C
import time

# The Soldered driver for the relay board, found in the lib folder of the examples repository.
from Relay import Relay, CHANNEL1

SDA_PIN = 8
SCL_PIN = 9

# The address switch on the module can put the relay anywhere from 0x30 to 0x37.
FIRST_RELAY_ADDRESS = 0x30
LAST_RELAY_ADDRESS = 0x37

i2c = I2C(0, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN))


def find_relay():
    """Returns the first address in the relay range that answers a scan, or None if none does."""
    for address in i2c.scan():
        if FIRST_RELAY_ADDRESS <= address <= LAST_RELAY_ADDRESS:
            return address
    return None


relay_address = find_relay()
print()

if relay_address is None:
    print("no relay answered between 0x30 and 0x37. Check the Qwiic cable.")
else:
    print("relay found at 0x{:02X}".format(relay_address))
    relay = Relay(i2c, relay_address)
    relay_on = False

    while True:
        """
        The loop only exists when a relay was found, so a missing relay is reported once and then left alone
        instead of being talked to.
        """
        relay_on = not relay_on
        relay.relayControl(CHANNEL1, 1 if relay_on else 0)

        print("relay on" if relay_on else "relay off")

        # Six seconds is far slower than the contacts need, and it keeps the number of operations low.
        time.sleep_ms(6000)
