"""
@file       6.2_Checking_A_Sensor_Alert_Flag.py
@brief      The TMP117 keeps converting on its own and decides for itself when the temperature has left a band,
            then latches a flag. The board sleeps, wakes just long enough to read that one flag, and goes
            straight back to sleep unless the sensor has something to say.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Soldered Electronics
"""

from machine import Pin, I2C, RTC, deepsleep
import struct
import time

# The Soldered driver for the TMP117, found in the lib folder of this repository.
from tmp117 import TMP117, TMP117_CMODE, TMP117_CONVT, TMP117_PMODE, TMP117_ALERT

"""
The LED on IO38 blinks once whenever the sensor actually had something to report. Nothing else is wired, because
everything else travels down the Qwiic cable.

The TMP117 also has a hardware ALERT output, and on a breakout with the header fitted it can pull a wire low and
wake the processor with no code running at all. This example reaches the same decision over the bus instead: the
alert condition is a flag inside the sensor, and a flag can be read.
"""
LED_PIN = 38

SDA_PIN = 8
SCL_PIN = 9

TMP117_ADDRESS = 0x49

# Raising SLEEP_SECONDS does not make the board miss anything. The flag latches, so the sensor holds the fact until
# it is read. Checking less often makes the response slower, it does not lose the event, and that is the difference
# between a flag and a pulse.
SLEEP_SECONDS = 2
BAND_C = 1.0

"""
State that has to survive deep sleep goes in the RTC memory block, packed into one bytes object. The layout is:

  wake count, quiet count, last temperature, have-last flag, quiet work time, have-quiet flag

struct.pack turns those into bytes and struct.unpack turns them back, which is the MicroPython answer to the
RTC_DATA_ATTR variables the Arduino version declares one at a time.
"""
STATE_FORMAT = "<HHfBIB"

rtc_mem = RTC()

saved = rtc_mem.memory()
if len(saved) == struct.calcsize(STATE_FORMAT):
    wake_count, quiet_count, last_temperature, have_last, quiet_work_us, have_quiet = struct.unpack(
        STATE_FORMAT, saved)
else:
    wake_count, quiet_count, last_temperature, have_last, quiet_work_us, have_quiet = 0, 0, 0.0, 0, 0, 0


def save_state():
    rtc_mem.memory(struct.pack(
        STATE_FORMAT, wake_count, quiet_count, last_temperature, have_last, quiet_work_us, have_quiet))


first_boot = (wake_count == 0)

# Only the first boot waits for the console. The CH340 is a separate chip that stays connected to the computer
# while the processor sleeps, so the connection never drops. A board with native USB would disconnect every sleep.
if first_boot:
    time.sleep_ms(1000)

wake_count += 1

led = Pin(LED_PIN, Pin.OUT)
i2c = I2C(0, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN))

# Everything above this line is the cost of waking up. Everything below it is this wake doing its job.
startup_us = time.ticks_us()

# 0x49 because JP2 on the breakout ties ADD0 high.
tmp = TMP117(i2c, TMP117_ADDRESS)


def blink(times):
    for _ in range(times):
        led.value(1)
        time.sleep_ms(120)
        led.value(0)
        time.sleep_ms(120)


def sleep_again():
    save_state()
    deepsleep(SLEEP_SECONDS * 1000)


def configure_sensor():
    """
    Configure once, on the first boot. The TMP117 stores its configuration in its own EEPROM, so it keeps these
    settings through deep sleep, a reset and a power cut, and rewriting them every wake would burn that write budget
    for nothing.

    setAlertMode(ALERT) is the line that matters most: init() leaves the sensor in data-ready mode, where the flag
    is raised after every conversion, which would report an alert on every check.
    """
    tmp.init(None)
    tmp.setConvMode(TMP117_CMODE.CONTINUOUS)
    tmp.setConvTime(TMP117_CONVT.C1S)
    tmp.setAlertMode(TMP117_PMODE.ALERT)

    print("sensor set to alert mode, one conversion per second")


def set_band_around(celsius):
    """The limits live in the sensor, not here, so once written the processor can be switched off entirely and the
    comparison still happens once a second."""
    tmp.setAlertTemperature(celsius - BAND_C, celsius + BAND_C)

    print("band is now {:.2f} to {:.2f} C. Put a finger on the sensor.".format(celsius - BAND_C, celsius + BAND_C))

    # Clear anything the old band left latched, or the next check reports an alert that has already been handled.
    tmp.readConfig()


if first_boot:
    print()
    print("6.2 checking a sensor alert flag")
    configure_sensor()

"""
The one read that matters. In alert mode the flags at the top of the config register latch until the register is
read, and this driver's readConfig() both reports them through getAlertType() and clears them, so one call asks the
question and re-arms the sensor.

Skipping it is the classic fault on this sensor. On the wired version of this circuit the alert pin stays low, the
board wakes the instant it sleeps, and it loops forever at full power.

The read is wrapped because MicroPython raises OSError when nothing answers, rather than handing back a plausible
number the way the Arduino driver does.
"""
try:
    tmp.readConfig()
    alert = tmp.getAlertType()
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

# Nothing has been measured yet, so put a band around wherever the room is now and start from there.
if first_boot:
    set_band_around(tmp.getTemperature())
    sleep_again()

# The quiet path, and the point of the example: two registers read and already on the way back to sleep. One dot is
# printed so you can watch the checks go by.
if alert == TMP117_ALERT.NOALERT:
    quiet_count += 1
    print(".", end="")
    quiet_work_us = time.ticks_diff(time.ticks_us(), startup_us)
    have_quiet = 1
    sleep_again()

# Something happened. This is the only path that costs anything.
celsius = tmp.getTemperature()

print()
print("wake {}: {}, now {:.3f} C".format(
    wake_count,
    "rose past the top of the band" if alert == TMP117_ALERT.HIGHALERT else "fell past the bottom of the band",
    celsius))

if quiet_count > 0:
    print("{} {} before this one found nothing".format(quiet_count, "check" if quiet_count == 1 else "checks"))

if have_last:
    print("change since the last alert: {:.3f} C".format(celsius - last_temperature))

last_temperature = celsius
have_last = 1
quiet_count = 0

set_band_around(celsius)

# Three numbers: what a wake costs before your code runs, what an alert needs on top, and what a check that found
# nothing needed. On this board the fixed cost dominates, so doing less while awake saves less than not waking at
# all. Try SLEEP_SECONDS at 30 and watch what happens to the run.
alert_work_us = time.ticks_diff(time.ticks_us(), startup_us)

line = "waking up cost {:.1f} ms, this alert {:.1f} ms on top".format(startup_us / 1000.0, alert_work_us / 1000.0)
if have_quiet:
    line += ", a check that found nothing {:.1f} ms".format(quiet_work_us / 1000.0)
print(line)

blink(1)
sleep_again()

"""
In 6.1 a timer woke the board and the board did all the thinking, running a conversion and some arithmetic to learn
nothing. Here the threshold lives in the sensor, which converts once a second at a few microamps against limits the
processor wrote once and forgot.

The timings say where that pays. Trimming the work to two register reads saves less than you would hope, because
most of a wake is spent waking. What the sensor bought is permission to wake far less often, and a board with the
alert pin on a wire would not need to check at all.

The processor is no longer in charge of the system: it is a resource the sensor calls on.
"""
