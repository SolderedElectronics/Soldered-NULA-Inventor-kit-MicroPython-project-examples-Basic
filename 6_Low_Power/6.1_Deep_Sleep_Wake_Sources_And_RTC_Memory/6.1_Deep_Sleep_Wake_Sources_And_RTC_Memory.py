"""
@file       6.1_Deep_Sleep_Wake_Sources_And_RTC_Memory.py
@brief      Two counters show what survives deep sleep and what does not. The board sleeps on a timer, on a
            button, on either, and finally on the onboard RTC's alarm at the start of the next minute.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Soldered Electronics
"""

from machine import Pin, I2C, RTC, deepsleep, wake_reason
import machine
import esp32
import time

# The Soldered driver for the PCF85063A, found in the lib folder of this repository.
from pcf85063a import PCF85063A

"""
The button is on IO21 and the LED on IO38.

IO21 needs a pull-up resistor of its own here, which it did not in example 2.1: the internal pull-up switches off
while the chip is asleep, so a wake pin left to float drifts down, looks like a press, and wakes the board over and
over. It is also one of this chip's RTC-capable pins, IO0 to IO21, and only those can wake it from deep sleep.
"""
BUTTON_PIN = 21
LED_PIN = 38

SDA_PIN = 8
SCL_PIN = 9

"""
  MODE_TIMER      sleep for a fixed number of seconds
  MODE_BUTTON     sleep until the button is pressed, with no timer at all
  MODE_EITHER     both, and the script reports which one woke it
  MODE_RTC_ALARM  wake at the start of the next minute, from the RTC on the board
"""
MODE_TIMER = 0
MODE_BUTTON = 1
MODE_EITHER = 2
MODE_RTC_ALARM = 3

MODE = MODE_RTC_ALARM

SLEEP_SECONDS = 10

# The two deliberate pauses, named so the awake time can say how much of itself was work and how much was waiting.
# The serial wait gives the USB port time to come back; without it the first lines of a boot are lost. A logger
# nobody is watching sets both to 0.
SERIAL_WAIT_MS = 1000
BLINK_MS = 200

"""
The onboard PCF85063A sits on the same I2C bus as the Qwiic connector at 0x51. Its interrupt output goes to IO17,
inside the board and not on a header, already pulled up to 3V3 there, so MODE_RTC_ALARM needs nothing wired.

That mode also arms a timer as a safety net: if the alarm is set to a time that cannot arrive, the board still comes
back and says the timer woke it.
"""
RTC_INT_PIN = 17
RTC_SAFETY_TIMEOUT_S = 90

"""
MicroPython has no RTC_DATA_ATTR. The equivalent is the RTC's own memory block, which stays powered while the rest
of the chip is off: RTC().memory() with no argument reads it back, and with a bytes argument writes it.

One byte here is enough for a boot counter. An ordinary variable is used alongside it for comparison.
"""
rtc_mem = RTC()
saved = rtc_mem.memory()
rtc_boot_count = saved[0] if len(saved) >= 1 else 0

normal_boot_count = 0

led = Pin(LED_PIN, Pin.OUT)
button = Pin(BUTTON_PIN, Pin.IN)

time.sleep_ms(SERIAL_WAIT_MS)

rtc_boot_count = (rtc_boot_count + 1) & 0xFF
normal_boot_count += 1
rtc_mem.memory(bytes([rtc_boot_count]))


def wakeup_reason_name():
    reason = wake_reason()
    if reason == machine.TIMER_WAKE:
        return "timer"
    if reason == machine.EXT0_WAKE:
        return "a pin (button or RTC alarm)"
    if reason == machine.EXT1_WAKE:
        return "a pin group"
    return "power on or reset, not a wake"


def print_awake_time(cycle_ms):
    """
    The fraction of each cycle spent awake is the number that decides how long the board runs on a limited supply,
    and unlike current it needs no meter: the chip draws milliamps awake and microamps asleep, so multiplying that
    fraction by the two datasheet figures gives an estimate you measured yourself.

    Watch how much of it is the serial wait and the blink rather than work, which is why 7.2 times each phase
    separately instead of the boot as a whole.
    """
    awake_ms = time.ticks_ms()
    overhead_ms = SERIAL_WAIT_MS + BLINK_MS

    line = "awake for {} ms".format(awake_ms)
    if cycle_ms > 0:
        line += " of every {} ms  ({:.1f} %)".format(cycle_ms, 100.0 * awake_ms / cycle_ms)
    print(line)

    work_ms = awake_ms - overhead_ms if awake_ms > overhead_ms else 0
    print("  of which {} ms is the serial wait and the blink, so the work took {} ms".format(overhead_ms, work_ms))


print()
print("RTC memory counter:  {}".format(rtc_boot_count))
print("ordinary counter:    {}".format(normal_boot_count))

# The ordinary counter reads 1 every time. Deep sleep is not pausing: the chip stops and starts again from the top
# of the script with every variable back at its initial value, as if you had pressed reset.

print("woken by: {}".format(wakeup_reason_name()))

# Blink so there is something to see from across the room.
led.value(1)
time.sleep_ms(BLINK_MS)
led.value(0)

# Peripherals do not survive either. I2C, PWM, Wi-Fi and anything a driver set up have to be created again on every
# wake. Forgetting this gives a script that works once and then quietly stops.
i2c = I2C(0, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN))

if MODE == MODE_TIMER:
    # The argument is in milliseconds.
    print("sleeping for {} seconds".format(SLEEP_SECONDS))
    print_awake_time(SLEEP_SECONDS * 1000)

    deepsleep(SLEEP_SECONDS * 1000)

elif MODE == MODE_BUTTON:
    # No timer at all: the board stays asleep indefinitely until the button pulls IO21 to ground. ext0 watches one
    # RTC-capable pin for one level. Sleeping is only useful if something can wake you.
    print("sleeping until the button is pressed")
    print_awake_time(0)

    esp32.wake_on_ext0(pin=button, level=esp32.WAKEUP_ALL_LOW)
    deepsleep()

elif MODE == MODE_EITHER:
    print("sleeping for up to {} seconds, or until the button is pressed".format(SLEEP_SECONDS))
    print_awake_time(SLEEP_SECONDS * 1000)

    esp32.wake_on_ext0(pin=button, level=esp32.WAKEUP_ALL_LOW)
    deepsleep(SLEEP_SECONDS * 1000)

else:
    """
    An interval and a schedule are different things. A timer wake sleeps ten seconds from whenever the last boot
    finished, so every wake adds that boot's length to the gap and they drift steadily later. The RTC is not
    counting from now, it is holding the time, so an alarm on the zeroth second fires at the start of every minute
    forever. Leave this running for ten minutes and check the timestamps.
    """
    rtc = PCF85063A(i2c)

    # Set the clock once so the printed times mean something. After that it runs on its own, through deep sleep and
    # through a power cut if a backup supply is fitted.
    if rtc_boot_count == 1:
        # set_time takes second, minute, hour, weekday, day, month, year.
        rtc.set_time(0, 0, 12, 1, 1, 1, 2026)

    year, month, day, weekday, hour, minute, second = rtc.get_time()
    print("RTC says {:02d}:{:02d}:{:02d}".format(hour, minute, second))

    # Clear the flag the last alarm left set, or the INT pin stays low and the board wakes the instant it sleeps.
    rtc.clear_alarm()

    # 99 in any field means "do not care about this one".
    rtc.set_alarm(0, 99, 99, 99, 99)

    print("sleeping until the RTC alarm at the start of the next minute")
    print_awake_time(60000)

    rtc_int = Pin(RTC_INT_PIN, Pin.IN)
    esp32.wake_on_ext0(pin=rtc_int, level=esp32.WAKEUP_ALL_LOW)

    # The safety net described at the top of this file.
    deepsleep(RTC_SAFETY_TIMEOUT_S * 1000)

"""
Measuring this board's current: reading it over USB tells you nothing useful, because the CH340 stays enumerated and
draws far more than the sleeping processor. The onboard WS2812B also leaks a little even when dark, and opening JP1
is part of getting down to single-digit microamps.
"""
