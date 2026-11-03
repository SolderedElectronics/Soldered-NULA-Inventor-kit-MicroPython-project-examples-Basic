"""
@file       10a_Wake_Reason_Helper.py
@brief      Two counters show what survives deep sleep and what does not. The board blinks, then sleeps for ten seconds
            and wakes itself on a timer.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, RTC, deepsleep
import machine
import time

# The LED is on IO38.
LED_PIN = 38

# How long the board sleeps between wakes.
SLEEP_SECONDS = 10

# The two deliberate pauses, named so the awake time can say how much of itself was work and how much was waiting.
# The serial wait gives the USB port time to come back; without it the first lines of a boot are lost.
SERIAL_WAIT_MS = 1000
BLINK_MS = 200

# MicroPython has no RTC_DATA_ATTR. The equivalent is the RTC's own memory block, which stays powered while the rest
# of the chip is off: RTC().memory() with no argument reads it back, and with a bytes argument writes it.
# One byte is enough for a boot counter. An ordinary variable is used alongside it for comparison.
rtc_mem = RTC()
saved = rtc_mem.memory()
rtc_boot_count = saved[0] if len(saved) >= 1 else 0

normal_boot_count = 0


# Says in words what woke the board.
def wakeup_reason_name():
    reason = machine.wake_reason()
    if reason == machine.TIMER_WAKE:
        return "timer"
    if reason == machine.EXT0_WAKE:
        return "a pin (button or RTC alarm)"
    return "power on or reset, not a wake"


led = Pin(LED_PIN, Pin.OUT)

time.sleep_ms(SERIAL_WAIT_MS)

rtc_boot_count = (rtc_boot_count + 1) & 0xFF
normal_boot_count += 1
rtc_mem.memory(bytes([rtc_boot_count]))

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

print("sleeping for {} seconds".format(SLEEP_SECONDS))

awake_ms = time.ticks_ms()
overhead_ms = SERIAL_WAIT_MS + BLINK_MS
work_ms = awake_ms - overhead_ms if awake_ms > overhead_ms else 0

print("awake for {} ms of every {} ms  ({:.1f} %)".format(awake_ms, SLEEP_SECONDS * 1000, 100.0 * awake_ms / (SLEEP_SECONDS * 1000)))
print("  of which {} ms is the serial wait and the blink, so the work took {} ms".format(overhead_ms, work_ms))

# The argument is in milliseconds.
deepsleep(SLEEP_SECONDS * 1000)
