"""
@file       6.1_Deep_Sleep_Button_Wake.py
@brief      Two counters show what survives deep sleep and what does not. The board blinks, then sleeps with no timer
            at all and wakes only when the button is pressed.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, RTC, deepsleep
import machine
import esp32
import time

# The button is on IO21 and the LED on IO38.
#
# IO21 needs a pull-up resistor of its own here, which it did not in T7: the internal pull-up switches off
# while the chip is asleep, so a wake pin left to float drifts down, looks like a press, and wakes the board over and
# over. It is also one of this chip's RTC-capable pins, IO0 to IO21, and only those can wake it from deep sleep.
BUTTON_PIN = 21
LED_PIN = 38

# The two deliberate pauses, named so the awake time can say how much of itself was work and how much was waiting.
# The serial wait gives the USB port time to come back; without it the first lines of a boot are lost.
SERIAL_WAIT_MS = 1000
BLINK_MS = 200

# MicroPython has no RTC_DATA_ATTR. The equivalent is the RTC's own memory block, which stays powered while the rest
# of the chip is off: RTC().memory() with no argument reads it back, and with a bytes argument writes it.
# One byte is enough for a boot counter. An ordinary variable is used alongside it for comparison.
rtc_mem = RTC()
saved = rtc_mem.memory()

# The very first run finds the block empty, so the count starts at 0.
if len(saved) == 0:
    rtc_boot_count = 0
else:
    rtc_boot_count = saved[0]

normal_boot_count = 0

led = Pin(LED_PIN, Pin.OUT)
button = Pin(BUTTON_PIN, Pin.IN)

time.sleep_ms(SERIAL_WAIT_MS)

# One byte only holds 0 to 255, so after 255 the count starts again from 0.
rtc_boot_count = rtc_boot_count + 1
if rtc_boot_count > 255:
    rtc_boot_count = 0
normal_boot_count = normal_boot_count + 1
rtc_mem.memory(bytes([rtc_boot_count]))

print()
print("RTC memory counter:  {}".format(rtc_boot_count))
print("ordinary counter:    {}".format(normal_boot_count))

# The ordinary counter reads 1 every time. Deep sleep is not pausing: the chip stops and starts again from the top
# of the script with every variable back at its initial value, as if you had pressed reset.

# Ask the chip what woke it and keep the answer as words. The starting text is for the case where none of the wake
# sources below fired, which means the board was just powered on or reset.
wake_reason_text = "power on or reset, not a wake"
if machine.wake_reason() == machine.TIMER_WAKE:
    wake_reason_text = "timer"
if machine.wake_reason() == machine.EXT0_WAKE:
    wake_reason_text = "a pin (button or RTC alarm)"

print("woken by: {}".format(wake_reason_text))

# Blink so there is something to see from across the room.
led.value(1)
time.sleep_ms(BLINK_MS)
led.value(0)

print("sleeping until the button is pressed")

awake_ms = time.ticks_ms()
overhead_ms = SERIAL_WAIT_MS + BLINK_MS
work_ms = awake_ms - overhead_ms

print("awake for {} ms".format(awake_ms))
print("  of which {} ms is the serial wait and the blink, so the work took {} ms".format(overhead_ms, work_ms))

# No timer at all: the board stays asleep until the button pulls IO21 to ground. ext0 watches one RTC-capable pin
# for one level.
esp32.wake_on_ext0(pin=button, level=esp32.WAKEUP_ALL_LOW)
deepsleep()
