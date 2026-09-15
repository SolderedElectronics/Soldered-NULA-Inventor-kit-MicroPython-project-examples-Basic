"""
@file       7.2_WiFi_Temperature_Logger.py
@brief      Sends a message every minute, the moment the temperature moves a full degree, or whenever the button
            is pressed. Between those it wakes every two seconds to ask the sensor one question, and sleeps.
            Times every phase so you can see where the energy goes.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Soldered Electronics
"""

from machine import Pin, I2C, RTC, deepsleep, wake_reason
import machine
import esp32
import network
import urequests
import neopixel
import struct
import time

# The Soldered drivers for the TMP117 and the PCF85063A, found in the lib folder of this repository.
from tmp117 import TMP117, TMP117_CMODE, TMP117_CONVT, TMP117_PMODE, TMP117_ALERT
from pcf85063a import PCF85063A

# Fill these in before running. The board joins 2.4 GHz networks.
SSID = "your ssid"
PASSWORD = "your password"

# Open https://webhook.site, copy the unique link it gives you, and paste it here. Anything you send shows up on
# that page as it arrives.
UPLOAD_URL = "your unique url"

"""
The only thing on the breadboard is the button on IO21, and the only thing on the Qwiic cable is the sensor. The
RGB LED and the RTC are already on the board.

The button needs a 10 kOhm to 3V3 of its own, because the internal pull-ups switch off during deep sleep and the
pin would otherwise float and wake the board at random. Example 6.1 goes into this.
"""
BUTTON_PIN = 21

# The onboard PCF85063A interrupt output, internal to the board and already pulled up there, so nothing to wire.
RTC_INT_PIN = 17

# The onboard WS2812B.
RGB_PIN = 2

SDA_PIN = 8
SCL_PIN = 9

TMP117_ADDRESS = 0x49

"""
The two things that make the board send: a full degree of movement since the last message, and the clock.

CHANGE_C is written into the sensor as a band either side of the last reading sent, so the TMP117 watches for it
once a second while the processor is off, and latches the answer.

One minute is short for a real logger and is here so the example can be watched. A logger left running for a week
would use fifteen or sixty, and nothing else would change.
"""
CHANGE_C = 1.0
LOG_INTERVAL_MINUTES = 1

"""
How often the board wakes just to ask whether that degree has happened yet. This is what "immediately" costs: the
board cannot feel the temperature while asleep and the alert pin is not wired, so the only way to react inside a
minute is to wake and look. Example 6.2 measured what one of these checks costs.
"""
CHECK_SECONDS = 2

"""
The ring buffer lives in RTC memory, so it survives deep sleep. A reading that fails to upload stays in it and goes
up on the next wake, and several readings travel in one connection. Twelve covers twelve minutes at one a minute,
and when it fills the oldest is dropped.

MicroPython has no RTC_DATA_ATTR, so everything that has to survive is packed into the RTC memory block with
struct: a fixed header followed by one (timestamp, temperature) pair per buffered reading.
"""
BUFFER_SIZE = 12
HEADER_FORMAT = "<HHfBB"
ENTRY_FORMAT = "<If"

rtc_mem = RTC()


def load_state():
    saved = rtc_mem.memory()
    header_size = struct.calcsize(HEADER_FORMAT)

    if len(saved) < header_size:
        return 0, 0, 0.0, 0, []

    wake, count, last_temp, have, _pad = struct.unpack(HEADER_FORMAT, saved[:header_size])

    entries = []
    entry_size = struct.calcsize(ENTRY_FORMAT)
    for i in range(count):
        start = header_size + i * entry_size
        if start + entry_size <= len(saved):
            entries.append(struct.unpack(ENTRY_FORMAT, saved[start:start + entry_size]))

    return wake, count, last_temp, have, entries


def save_state():
    blob = struct.pack(HEADER_FORMAT, wake_count, len(buffer), last_sent_temperature, have_sent, 0)
    for stamp, celsius in buffer:
        blob += struct.pack(ENTRY_FORMAT, stamp, celsius)
    rtc_mem.memory(blob)


wake_count, _count, last_sent_temperature, have_sent, buffer = load_state()

first_boot = (wake_count == 0)

# Only the first boot waits for the console. The CH340 stays connected to the computer while the processor sleeps,
# so the connection never drops.
if first_boot:
    time.sleep_ms(1000)

wake_count += 1

i2c = I2C(0, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN))

# Everything above this line is the cost of waking up. Everything below it is this wake doing its job.
startup_us = time.ticks_us()

tmp = TMP117(i2c, TMP117_ADDRESS)
rtc = PCF85063A(i2c)
rgb = neopixel.NeoPixel(Pin(RGB_PIN), 1)


def set_led(r, g, b):
    rgb[0] = (r, g, b)
    rgb.write()


def clock_string(stamp):
    """Seconds since midnight as hh:mm:ss. The buffer stores one number per reading because a number is cheap to
    keep in RTC memory; turning it into something readable happens once, where a human will look at it."""
    return "{:02d}:{:02d}:{:02d}".format(stamp // 3600, (stamp // 60) % 60, stamp % 60)


def configure_sensor():
    """Configure once, on the first boot: the TMP117 keeps this in its own EEPROM through sleep, reset and power
    cuts. setAlertMode(ALERT) is the line that matters, since init() leaves it in data-ready mode where the flag is
    raised after every conversion, reporting a change on every wake."""
    tmp.init(None)
    tmp.setConvMode(TMP117_CMODE.CONTINUOUS)
    tmp.setConvTime(TMP117_CONVT.C1S)
    tmp.setAlertMode(TMP117_PMODE.ALERT)


def set_band_around(celsius):
    """The limits live in the sensor, so the comparison keeps happening at a few microamps with the processor off.
    They are ordinary registers, unlike the mode settings, so writing them costs no EEPROM."""
    tmp.setAlertTemperature(celsius - CHANGE_C, celsius + CHANGE_C)

    # Clear anything the old band left latched, or the next wake reports a change that has already been handled.
    tmp.readConfig()


def take_reading():
    """Returns the reading just taken, or None if there was no sensor to take it from."""
    try:
        if tmp.getDeviceID() != 0x117:
            print("no TMP117 answering. Check the Qwiic cable. Nothing logged this wake.")
            return None
        celsius = tmp.getTemperature()
    except OSError as e:
        print("no answer from the bus: {}. Nothing logged this wake.".format(e))
        return None

    # From the RTC, not ticks_ms(), which restarts at zero on every wake and says nothing about when this happened.
    _year, _month, _day, _weekday, hour, minute, second = rtc.get_time()
    stamp = hour * 3600 + minute * 60 + second

    buffer.append((stamp, celsius))
    # Full. Drop the oldest, which is the right thing to lose if a network has been down for an hour.
    while len(buffer) > BUFFER_SIZE:
        buffer.pop(0)

    print("logged {:.3f} C at {}, buffer holds {}".format(celsius, clock_string(stamp), len(buffer)))

    return celsius


def upload_buffer(reason):
    """
    Time every phase separately, because these numbers are the point of the example. Association takes seconds; the
    upload itself, once associated, takes a fraction of that. Uploading twelve readings costs barely more than one,
    because the expensive part happened before the first byte of data moved.

    On a board that has to last, connecting less often and sending more each time is worth far more than sending
    less. Wi-Fi is a power decision before it is a feature, which is why this is the only example that uses it.
    """
    connect_start = time.ticks_ms()

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)

    while not wlan.isconnected() and time.ticks_diff(time.ticks_ms(), connect_start) < 20000:
        time.sleep_ms(100)

    connect_ms = time.ticks_diff(time.ticks_ms(), connect_start)

    if not wlan.isconnected():
        print("association failed after {} ms. Readings stay in the buffer for next time.".format(connect_ms))
        wlan.active(False)
        return 0

    print("associated in {} ms".format(connect_ms))

    # Two lines saying who sent this and why, then one line per reading. The unit goes on every line, not in a
    # heading: whoever reads this log will be scrolling rather than starting from the top.
    payload = "device: NULA DeepSleep ESP32-S3\n"
    payload += "reason: {}\n".format(reason)
    for stamp, celsius in buffer:
        payload += "{}, {:.3f} C\n".format(clock_string(stamp), celsius)

    post_start = time.ticks_ms()

    code = 0
    try:
        # Say what the body is, so the far end shows it as plain lines rather than guessing at a format.
        response = urequests.post(UPLOAD_URL, data=payload, headers={"Content-Type": "text/plain"})
        code = response.status_code
        response.close()
    except Exception as e:
        print("upload raised {}".format(e))

    post_ms = time.ticks_diff(time.ticks_ms(), post_start)

    print("POST took {} ms, response {}".format(post_ms, code))

    wlan.active(False)

    if code <= 0:
        print("upload failed. Readings stay in the buffer.")
        return 0

    sent = len(buffer)
    del buffer[:]

    print("sent {} {}. Association was {:.0f} % of the time the radio was on.".format(
        sent, "reading" if sent == 1 else "readings", connect_ms / (connect_ms + post_ms) * 100.0))

    return sent


def sleep_again(rearm_alarm):
    """
    Three wake sources at once, none needing a wire. The timer is the fast one, asking the sensor every
    CHECK_SECONDS whether the temperature moved, which is how a change gets reported in seconds rather than at the
    next minute. It is the only way to do it here: the TMP117 breakout's ALERT output is on a header that ships
    unpopulated, and nothing in this kit needs soldering. The RTC alarm is the heartbeat, and the button is there so
    you can ask for a message.
    """
    # Only touch the alarm on the wake it fired. Arming it is what clears the flag and releases IO17, and the
    # target is worked out from the time now, so re-arming on every check would push it further away forever.
    if rearm_alarm:
        _y, _mo, _d, _wd, _h, minute, _s = rtc.get_time()
        next_minute = (minute + LOG_INTERVAL_MINUTES) % 60
        rtc.clear_alarm()
        rtc.set_alarm(0, next_minute, 99, 99, 99)
        print("next alarm at minute {}".format(next_minute))

    save_state()

    # ext1 watches a group of pins rather than one, so both the RTC and the button can wake the board. Both lines
    # idle high through a pull-up: the RTC's on the board, the button's on the breadboard. On the S3 this level
    # setting fires when any pin in the group goes low.
    esp32.wake_on_ext1(pins=(Pin(RTC_INT_PIN, Pin.IN), Pin(BUTTON_PIN, Pin.IN)), level=esp32.WAKEUP_ALL_LOW)

    # The fast check.
    deepsleep(CHECK_SECONDS * 1000)


if first_boot:
    print()
    print("7.2 wifi temperature logger")
    rtc.set_time(0, 0, 12, 1, 1, 1, 2026)
    configure_sensor()

# Ask whether anything happened while the processor was off. The flags latch until the config register is read, and
# reading it both asks and re-arms, so this must come before anything else touches the sensor.
try:
    tmp.readConfig()
    changed = tmp.getAlertType() != TMP117_ALERT.NOALERT
except OSError as e:
    print("no answer from the bus: {}. Check the Qwiic cable.".format(e))
    sleep_again(False)
    changed = False

reason_code = wake_reason()
alarm_wake = (reason_code == machine.EXT1_WAKE) or first_boot
button_wake = Pin(BUTTON_PIN, Pin.IN).value() == 0

# Most wakes are the two-second check and find nothing. Those cost two register reads and go straight back to sleep,
# with one dot printed. That is 6.2's quiet path, and it is what makes an immediate response affordable.
if not alarm_wake and not button_wake and not changed:
    print(".", end="")
    sleep_again(False)

print()
print("wake {} by {}".format(
    wake_count,
    "the button" if button_wake else "the RTC alarm" if alarm_wake else "the check timer, sensor flagged a change"))

latest = take_reading()

full = len(buffer) >= BUFFER_SIZE

if buffer:
    # Why this connection happened travels with the readings, so the log explains itself. A change is named ahead of
    # the schedule because when both are true, the change is the news.
    if button_wake:
        reason = "button pressed"
    elif changed:
        reason = "temperature changed by a full degree"
    elif full:
        reason = "buffer full"
    else:
        reason = "scheduled upload"

    print("connecting because of {}".format(reason))

    # The RGB LED reports the phase, because a board that spends its life asleep usually has nobody watching serial.
    set_led(0, 0, 40)
    uploaded = upload_buffer(reason)
    set_led(0, 40, 0) if uploaded > 0 else set_led(40, 0, 0)
    time.sleep_ms(300)
    set_led(0, 0, 0)

    # Move the band only when the message actually went. A failed upload leaves the sensor watching the old mark,
    # which is right: nothing has been reported, so nothing has moved as far as the log is concerned.
    if uploaded > 0 and latest is not None:
        last_sent_temperature = latest
        have_sent = 1
        set_band_around(latest)
else:
    print("nothing in the buffer, so the radio stays off")

# The cost of being awake against the cost of the work. On a board that sleeps between readings the first number is
# usually the larger one, and it is the same whether the radio ran or not.
print("waking up cost {:.1f} ms, this wake did {:.1f} ms of work on top".format(
    startup_us / 1000.0, time.ticks_diff(time.ticks_us(), startup_us) / 1000.0))

sleep_again(alarm_wake)

"""
Every other example spends energy on the thing it is measuring. This one spends it on talking, and the difference in
scale is the lesson: a temperature reading is a couple of milliseconds, joining a Wi-Fi network is two or three
thousand. The radio is a different order of magnitude, and treating it as just another feature costs you the whole
power budget.

Both intervals here are set for watching rather than lasting, and moving them is the exercise.
LOG_INTERVAL_MINUTES at 60 sends one message an hour holding twelve readings, one association instead of sixty, and
the data that arrives is identical. CHECK_SECONDS at 30 turns "within two seconds" into "within thirty" and drops
the checking cost fifteen-fold. Neither changes a line of code. The only way to choose them is to decide how late a
report is still useful.
"""
