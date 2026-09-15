"""
@file       5.2_Relay_Switching_With_Hysteresis_And_Lockout.py
@brief      Switches a Qwiic relay from a pot. A hysteresis band keeps a noisy input from chattering the
            contacts, and a minimum switching interval keeps a request made during the lockout instead of
            dropping it.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Soldered Electronics
"""

from machine import Pin, I2C, ADC
import time

# The Soldered driver for the relay board, found in the lib folder of this repository.
from Relay import Relay, CHANNEL1

"""
The relay is on the Qwiic bus, the pot is on IO4, and the LED on IO38 shows what the sketch wants the relay to do,
which is not always what the relay is allowed to do.

The module's address is set by a switch on the module and can be anything from 0x30 to 0x37. Run the scanner from
example 5.1 if 0x30 gives you nothing.
"""
SDA_PIN = 8
SCL_PIN = 9
RELAY_ADDRESS = 0x30

POT_PIN = 4
LED_PIN = 38

"""
  MODE_CLICK       switch it on and off once a second. Listen, and watch the settle time.
  MODE_HYSTERESIS  a band either side of the threshold, so a noisy input cannot chatter the contacts.
  MODE_LOCKOUT     a band, plus a minimum interval between switches.
"""
MODE_CLICK = 0
MODE_HYSTERESIS = 1
MODE_LOCKOUT = 2

MODE = MODE_LOCKOUT

# Threshold and band, in raw ADC counts out of 4095.
THRESHOLD = 2048
BAND = 300

# The shortest time the relay is allowed to stay in one state, in milliseconds.
LOCKOUT_MS = 5000

i2c = I2C(0, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN))
relay = Relay(i2c, RELAY_ADDRESS)

pot = ADC(Pin(POT_PIN), atten=ADC.ATTN_11DB)
led = Pin(LED_PIN, Pin.OUT)

# requested_state is what the input says the relay should be doing; actual_state is what it is actually doing. The
# distinction between them is the point of the second half of this page.
requested_state = False
actual_state = False
last_switch_ms = 0

print()

while True:
    if MODE == MODE_CLICK:
        # Everything driven so far settled in microseconds. This is a physical armature pulled across by a coil, and
        # it takes five to ten milliseconds to get there and stop bouncing.
        relay.relayControl(CHANNEL1, 1)
        led.value(1)
        print("on")
        time.sleep_ms(1000)

        relay.relayControl(CHANNEL1, 0)
        led.value(0)
        print("off")
        time.sleep_ms(1000)

    elif MODE == MODE_HYSTERESIS:
        # The same band as 2.3, somewhere getting it wrong is audible. Relay contacts are rated in operations, in
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

    else:
        """
        The band handles noise. It does nothing about a genuine change arriving too soon after the last one, and for
        a relay driving a compressor or a motor, switching back on straight away is worse than switching too often.

        A request made during the lockout is not thrown away. It sits in requested_state and the relay moves to it
        the moment the interval is up. Dropping it instead would leave the relay in whatever state happened to be
        current when the timer ran out. The same pattern comes back in 7.1 and 7.4.
        """
        raw = pot.read()

        if not requested_state and raw > THRESHOLD + BAND:
            requested_state = True
        elif requested_state and raw < THRESHOLD - BAND:
            requested_state = False

        led.value(1 if requested_state else 0)

        since_switch = time.ticks_diff(time.ticks_ms(), last_switch_ms)
        remaining = LOCKOUT_MS - since_switch if since_switch < LOCKOUT_MS else 0

        if requested_state != actual_state and remaining == 0:
            actual_state = requested_state
            last_switch_ms = time.ticks_ms()
            relay.relayControl(CHANNEL1, 1 if actual_state else 0)

        print("want {}  relay {}  lockout {:.1f} s".format(
            "on " if requested_state else "off",
            "on " if actual_state else "off",
            remaining / 1000.0))

        time.sleep_ms(200)

# Nothing on the breadboard drives this coil and there is no flyback diode to fit: both are on the module, with the
# chip that listens on the bus. Compare 4.3, where the transistor and the diode were yours to get right.
