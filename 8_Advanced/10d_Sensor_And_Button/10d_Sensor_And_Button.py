"""
@file       10d_Sensor_And_Button.py
@brief      The TMP117 watches a temperature band while the board sleeps. The board wakes every five seconds to read
            the sensor's alert flag, or at once when the button is pressed to print the temperature now.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, I2C, RTC, deepsleep
import machine
import esp32
import time

# The Soldered driver for the TMP117, found in the lib folder of this repository.
from tmp117 import TMP117, TMP117_CMODE, TMP117_CONVT, TMP117_PMODE, TMP117_ALERT

# The button is on IO21 (with its own pull-up to 3V3) and the LED on IO38. The TMP117 is on the Qwiic cable.
BUTTON_PIN = 21
LED_PIN = 38
SDA_PIN = 8
SCL_PIN = 9
TMP117_ADDRESS = 0x49

# How often the board wakes to read the flag if nobody presses the button.
SLEEP_SECONDS = 5

# The band is this many degrees Celsius either side of the temperature when it was last set.
BAND_C = 1.0

led = Pin(LED_PIN, Pin.OUT)
button = Pin(BUTTON_PIN, Pin.IN)
i2c = I2C(0, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN))
tmp = TMP117(i2c, TMP117_ADDRESS)
rtc_mem = RTC()

# Two bytes in RTC memory: whether the sensor has been configured yet, and how many alerts it has raised so far.
# After a power-on or a reset the memory is not trusted, so the script starts from the beginning.
configured = 0
alert_count = 0
saved = rtc_mem.memory()
if machine.reset_cause() == machine.DEEPSLEEP_RESET and len(saved) >= 2:
    configured = saved[0]
    alert_count = saved[1]


# Blinks the LED the given number of times.
def blink(times):
    for _ in range(times):
        led.value(1)
        time.sleep_ms(120)
        led.value(0)
        time.sleep_ms(120)


# Puts a band around the given temperature. The limits live in the sensor, so they keep working while the board
# sleeps. Reading the config register afterwards clears any flag the old band left behind.
def set_band_around(celsius):
    tmp.setAlertTemperature(celsius - BAND_C, celsius + BAND_C)
    tmp.readConfig()


def sleep_again():
    rtc_mem.memory(bytes([configured, alert_count & 0xFF]))

    # If the button is still held down, wait for it to be let go, or the board would wake again at once.
    while button.value() == 0:
        time.sleep_ms(10)

    # Both sources are armed, and whichever comes first wakes the board.
    esp32.wake_on_ext0(pin=button, level=esp32.WAKEUP_ALL_LOW)
    deepsleep(SLEEP_SECONDS * 1000)


first_boot = (configured == 0)
if first_boot:
    time.sleep_ms(1000)

# The sensor keeps its settings through sleep, so it is configured only once.
if first_boot:
    tmp.init(None)
    tmp.setConvMode(TMP117_CMODE.CONTINUOUS)
    tmp.setConvTime(TMP117_CONVT.C1S)
    tmp.setAlertMode(TMP117_PMODE.ALERT)

# MicroPython raises OSError when nothing answers, so a missing sensor is caught here.
try:
    tmp.readConfig()
    alert_type = tmp.getAlertType()
    device_id = tmp.getDeviceID()
except OSError as e:
    print()
    print("no answer from the bus: {}. Check the Qwiic cable.".format(e))
    blink(5)
    sleep_again()

if device_id != 0x117:
    print()
    print("device ID reads 0x{:X}, not 0x117. That is not a TMP117.".format(device_id))
    blink(5)
    sleep_again()

if first_boot:
    set_band_around(tmp.getTemperature())
    configured = 1
    print()
    print("sensor set up. Put a finger on it, or press the button.")
    sleep_again()

# The readConfig() call above already cleared the flags, and alert_type holds what they said.
alert = (alert_type != TMP117_ALERT.NOALERT)
celsius = tmp.getTemperature()

if machine.wake_reason() == machine.EXT0_WAKE:
    # The button was pressed: report the temperature now, whatever the flag says.
    print()
    print("button: {:.2f} C, alerts so far: {}".format(celsius, alert_count))
    blink(2)
elif alert:
    # The timer woke the board and the sensor had raised its flag.
    alert_count += 1
    print()
    print("alert {}: the temperature left the band, now {:.2f} C".format(alert_count, celsius))
    blink(1)
else:
    # Nothing to report. One dot so you can watch the checks go by.
    print(".", end="")

# After an alert, put a new band around where the temperature is now.
if alert:
    set_band_around(celsius)

sleep_again()
