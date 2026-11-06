"""
@file       5.2_Relay_Switching_With_Hysteresis_And_Lockout.py
@brief      Switches a Qwiic relay from a pot. A hysteresis band keeps a noisy input from chattering the
            contacts, and a minimum interval between switches protects them from fast requests.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, I2C, ADC
import time

# The Soldered driver for the relay board, found in the lib folder of this repository.
from Relay import Relay, CHANNEL1

"""
The relay is on the Qwiic bus, the pot is on IO4, and the LED on IO38 shows what the script wants the relay to do,
which is not always what the relay is allowed to do.

The module's address is set by a switch on the module and can be anything from 0x30 to 0x37. Run the scanner from
T21 if 0x30 gives you nothing.
"""
SDA_PIN = 8
SCL_PIN = 9
RELAY_ADDRESS = 0x30

POT_PIN = 4
LED_PIN = 38

# Threshold and band, in raw ADC counts out of 4095.
THRESHOLD = 2048
BAND = 300

# The shortest time the relay is allowed to stay in one state, in milliseconds.
LOCKOUT_MS = 5000

i2c = I2C(0, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN))
relay = Relay(i2c, RELAY_ADDRESS)

pot = ADC(Pin(POT_PIN), atten=ADC.ATTN_11DB)
led = Pin(LED_PIN, Pin.OUT)

# requested_state is what the knob says the relay should be doing; actual_state is what it is actually doing. The
# distinction between them is the point of this task.
requested_state = False
actual_state = False
last_switch_ms = 0

print()

while True:
    """
    The band handles noise. It does nothing about a genuine change arriving too soon after the last one, and for
    a relay driving a compressor or a motor, switching back on straight away is worse than switching too often.

    A request made during the lockout is not thrown away. It sits in requested_state and the relay moves to it
    the moment the interval is up. Dropping it instead would leave the relay in whatever state happened to be
    current when the timer ran out. The same pattern comes back in T26 and T29.
    """
    # Read the knob.
    raw = pot.read()

    # Work out what the knob is asking for. It only changes its mind once the knob is clearly past the band.
    if not requested_state and raw > THRESHOLD + BAND:
        requested_state = True
    elif requested_state and raw < THRESHOLD - BAND:
        requested_state = False

    # The LED always shows what was asked for.
    if requested_state:
        led.value(1)
    else:
        led.value(0)

    # How much of the lockout is left. It stays 0 once the relay has rested for long enough.
    remaining = 0
    since_switch = time.ticks_diff(time.ticks_ms(), last_switch_ms)
    if since_switch < LOCKOUT_MS:
        remaining = LOCKOUT_MS - since_switch

    # Move the relay only if it is not where the knob wants it and the lockout is over.
    if requested_state != actual_state and remaining == 0:
        actual_state = requested_state
        last_switch_ms = time.ticks_ms()

        if actual_state:
            relay.relayControl(CHANNEL1, 1)
        else:
            relay.relayControl(CHANNEL1, 0)

    # Print what was asked for, what the relay is doing and how long the lockout has left.
    if requested_state:
        want_text = "on "
    else:
        want_text = "off"

    if actual_state:
        relay_text = "on "
    else:
        relay_text = "off"

    print("want {}  relay {}  lockout {:.1f} s".format(want_text, relay_text, remaining / 1000.0))

    time.sleep_ms(200)

# Nothing on the breadboard drives this coil and there is no flyback diode to fit: both are on the module, with the
# chip that listens on the bus. Compare T17, where the transistor and the diode were yours to get right.
