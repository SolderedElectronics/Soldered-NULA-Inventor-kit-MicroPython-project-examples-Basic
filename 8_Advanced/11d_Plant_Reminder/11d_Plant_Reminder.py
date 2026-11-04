"""
@file       11d_Plant_Reminder.py
@brief      Sleeps for 30 seconds at a time. On each wake it reads the light and the temperature. If it has been dark
            for three wakes in a row, or the temperature is outside 18 to 28 C, it blinks the LED and chirps the
            buzzer for two seconds. Otherwise it goes straight back to sleep with the LED dark.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, I2C, ADC, PWM, RTC, deepsleep
import machine
import struct
import time

# The Soldered driver for the TMP117, found in the lib folder of this repository.
from tmp117 import TMP117

# The photoresistor divider is on IO4, the LED on IO38 and the buzzer's transistor on IO48. The TMP117 is on the
# Qwiic cable.
LIGHT_PIN = 4
LED_PIN = 38
BUZZER_PIN = 48
SDA_PIN = 8
SCL_PIN = 9
TMP117_ADDRESS = 0x49

# How long the board sleeps between two checks, in seconds.
SLEEP_SECONDS = 30

# A reading below this many counts means dark. This one is a starting value: take yours from the calibration in T11,
# with your finger over the photoresistor.
DARK_BELOW_COUNTS = 600

# The plant is happy between these two temperatures, in degrees Celsius.
COLDEST_OK_C = 18.0
WARMEST_OK_C = 28.0

# The reminder fires after this many dark wakes in a row.
DARK_WAKES_LIMIT = 3

# The reminder is five beeps of 200 ms with a 200 ms gap, which is two seconds. The buzzer pitch is the resonant
# frequency from T17, so use your own, and the duty of 25 % is the one T26 uses.
BEEP_COUNT = 5
BEEP_MS = 200
GAP_MS = 200
BUZZER_HZ = 2700
BUZZER_DUTY = (25 * 65535) // 100

# RTC memory holds bytes, not variables, so the two counters are packed into one block of bytes.
# "<IB" means: one unsigned 32-bit number (the wake count), then one unsigned byte (the dark wakes in a row).
STATE_FORMAT = "<IB"
STATE_SIZE = struct.calcsize(STATE_FORMAT)

led = Pin(LED_PIN, Pin.OUT, value=0)
light_sensor = ADC(Pin(LIGHT_PIN), atten=ADC.ATTN_11DB)
i2c = I2C(0, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN))
tmp = TMP117(i2c, TMP117_ADDRESS)
rtc_mem = RTC()

# After a power-on or a reset the memory is not trusted, so the counters start from zero.
wake_count = 0
dark_wakes = 0
saved = rtc_mem.memory()
if machine.reset_cause() == machine.DEEPSLEEP_RESET and len(saved) == STATE_SIZE:
    wake_count, dark_wakes = struct.unpack(STATE_FORMAT, saved)


def blink(times):
    """Blinks the LED the given number of times."""
    for _ in range(times):
        led.value(1)
        time.sleep_ms(120)
        led.value(0)
        time.sleep_ms(120)


def remind():
    """Blinks the LED and chirps the buzzer together for two seconds, then leaves both off."""
    buzzer = PWM(Pin(BUZZER_PIN), freq=BUZZER_HZ, duty_u16=0)

    for _ in range(BEEP_COUNT):
        led.value(1)
        buzzer.duty_u16(BUZZER_DUTY)
        time.sleep_ms(BEEP_MS)

        led.value(0)
        buzzer.duty_u16(0)
        time.sleep_ms(GAP_MS)

    # Hand the pin back, so nothing keeps driving the transistor while the board sleeps.
    buzzer.deinit()


def reason_to_remind(celsius):
    """Returns the reason for a reminder, or an empty text when the plant is fine. The temperature comes first because
    it needs no history, and the light needs the dark counter."""
    if celsius < COLDEST_OK_C:
        return "too cold"
    if celsius > WARMEST_OK_C:
        return "too warm"
    if dark_wakes >= DARK_WAKES_LIMIT:
        return "too dark"
    return ""


def sleep_again():
    """Saves the counters into RTC memory and stops the board for SLEEP_SECONDS. The script starts again from its
    first line when the timer runs out."""
    rtc_mem.memory(struct.pack(STATE_FORMAT, wake_count, min(dark_wakes, 255)))
    deepsleep(SLEEP_SECONDS * 1000)


first_boot = (wake_count == 0)
if first_boot:
    time.sleep_ms(1000)

# The sensor keeps its settings through sleep, so it is configured only once. The wait gives it time to finish its
# first one-second conversion.
if first_boot:
    tmp.init(None)
    time.sleep_ms(1100)

    print()
    print("plant reminder: a check every 30 s, a reminder when it is too dark, too cold or too warm")

# MicroPython raises an error when nothing answers, and the device ID catches the case where something answers but is
# not a TMP117. A failed wake is not counted and the dark counter is left alone.
try:
    device_id = tmp.getDeviceID()
    celsius = tmp.getTemperature()
except (OSError, IndexError):
    print("no answer from the bus. Check the Qwiic cable.")
    blink(5)
    sleep_again()

if device_id != 0x117:
    print("no TMP117 on the bus. Check the Qwiic cable.")
    blink(5)
    sleep_again()

light = light_sensor.read()
wake_count += 1

# Count the dark wakes in a row. One bright wake sets the count back to zero.
if light < DARK_BELOW_COUNTS:
    dark_wakes += 1
else:
    dark_wakes = 0

reason = reason_to_remind(celsius)

if reason == "":
    print("wake {}: light {}, {:.2f} C, dark {} in a row, ok".format(wake_count, light, celsius, dark_wakes))
else:
    print("wake {}: light {}, {:.2f} C, dark {} in a row, reminder: {}".format(
        wake_count, light, celsius, dark_wakes, reason))
    remind()

sleep_again()
