"""
@file       09d_Advanced_Thermostat.py
@brief      Switches a Qwiic relay from the TMP117 temperature, like a thermostat. Every reading is checked before it
            is used, a hysteresis band keeps the relay from chattering, and a lockout limits how often it may switch.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, I2C
import time

# The Soldered drivers, found in the lib folder of the examples repository.
from tmp117 import TMP117
from Relay import Relay, CHANNEL1

# The Qwiic bus is IO8 (SDA) and IO9 (SCL). Both modules share it and are told apart by their addresses, which are
# the ones from T29 and T30.
SDA_PIN = 8
SCL_PIN = 9
TMP117_ADDRESS = 0x49
RELAY_ADDRESS = 0x30

# The LED on IO38 shows what the script wants the relay to do, as it did in T30.
LED_PIN = 38

# The relay switches on above SET_POINT + HALF_BAND and off below SET_POINT - HALF_BAND, in degrees Celsius.
SET_POINT = 25.0
HALF_BAND = 0.5

# The shortest time the relay is allowed to stay in one state, in milliseconds.
LOCKOUT_MS = 10000

i2c = I2C(0, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN))
tmp = TMP117(i2c, TMP117_ADDRESS)
tmp.init(None)
relay = Relay(i2c, RELAY_ADDRESS)
led = Pin(LED_PIN, Pin.OUT)

requested_state = False
actual_state = False
last_switch_ms = 0

print()

while True:
    """
    The reading is checked first, exactly as in T29. If the bus does not answer or the device ID is wrong, the
    temperature is not a measurement, so the script leaves the relay where it is and tries again instead of acting
    on a number it cannot trust.
    """
    try:
        celsius = tmp.getTemperature()
        device_id = tmp.getDeviceID()
    except OSError as e:
        print("no answer from the bus: {}. Check the Qwiic cable.".format(e))
        time.sleep_ms(500)
        continue

    if device_id != 0x117:
        print("device ID reads wrong, so the temperature is not trusted. Check the Qwiic cable.")
        time.sleep_ms(500)
        continue

    # The hysteresis band from T30, with degrees in place of ADC counts.
    if not requested_state and celsius > SET_POINT + HALF_BAND:
        requested_state = True
    elif requested_state and celsius < SET_POINT - HALF_BAND:
        requested_state = False

    led.value(1 if requested_state else 0)

    # The lockout from T30: the relay only follows the request once it has rested for long enough.
    rested_long_enough = time.ticks_diff(time.ticks_ms(), last_switch_ms) >= LOCKOUT_MS
    if requested_state != actual_state and rested_long_enough:
        actual_state = requested_state
        last_switch_ms = time.ticks_ms()
        relay.relayControl(CHANNEL1, 1 if actual_state else 0)

    print("{:.2f} C  want {}  relay {}".format(
        celsius,
        "on " if requested_state else "off",
        "on " if actual_state else "off"))

    time.sleep_ms(500)
