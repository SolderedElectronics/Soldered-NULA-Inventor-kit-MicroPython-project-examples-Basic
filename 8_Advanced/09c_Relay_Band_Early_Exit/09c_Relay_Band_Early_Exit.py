"""
@file       09c_Relay_Band_Early_Exit.py
@brief      Switches a Qwiic relay from a pot, with a hysteresis band but no minimum interval between switches.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, I2C, ADC
import time

# The Soldered driver for the relay board, found in the lib folder of this repository.
from Relay import Relay, CHANNEL1

"""
The relay is on the Qwiic bus, the pot is on IO4, and the LED on IO38 shows the state the relay was switched to.

The module's address is set by a switch on the module and can be anything from 0x30 to 0x37. Run the scanner from
T28 if 0x30 gives you nothing.
"""
SDA_PIN = 8
SCL_PIN = 9
RELAY_ADDRESS = 0x30

POT_PIN = 4
LED_PIN = 38

# Threshold and band, in raw ADC counts out of 4095.
THRESHOLD = 2048
BAND = 300

i2c = I2C(0, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN))
relay = Relay(i2c, RELAY_ADDRESS)

pot = ADC(Pin(POT_PIN), atten=ADC.ATTN_11DB)
led = Pin(LED_PIN, Pin.OUT)

actual_state = False

print()

while True:
    # The same band as T15, somewhere getting it wrong is audible. Relay contacts are rated in operations, in
    # the tens or hundreds of thousands, and chatter spends that budget in minutes.
    raw = pot.read()

    if not actual_state and raw > THRESHOLD + BAND:
        actual_state = True
    elif actual_state and raw < THRESHOLD - BAND:
        actual_state = False
    else:
        time.sleep_ms(20)
        continue

    relay.relayControl(CHANNEL1, 1 if actual_state else 0)
    led.value(1 if actual_state else 0)

    print("switched to {} at {}".format("on" if actual_state else "off", raw))

    time.sleep_ms(20)
