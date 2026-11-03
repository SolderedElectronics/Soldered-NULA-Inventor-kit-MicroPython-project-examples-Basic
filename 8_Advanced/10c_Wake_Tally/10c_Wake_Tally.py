"""
@file       10c_Wake_Tally.py
@brief      The board sleeps for ten seconds or until the button is pressed. Every wake is counted by its source in
            RTC memory, and the LED blinks once for the timer and twice for the button.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, RTC, deepsleep
import machine
import esp32
import time

# The button is on IO21 and the LED on IO38. IO21 has its own 10 kOhm pull-up to 3V3 on the breadboard, because the
# internal one switches off while the chip sleeps.
BUTTON_PIN = 21
LED_PIN = 38

# How long the board sleeps if nobody presses the button.
SLEEP_SECONDS = 10

led = Pin(LED_PIN, Pin.OUT)
button = Pin(BUTTON_PIN, Pin.IN)

rtc_mem = RTC()


# Blinks the LED the given number of times.
def blink(times):
    for _ in range(times):
        led.value(1)
        time.sleep_ms(150)
        led.value(0)
        time.sleep_ms(150)


time.sleep_ms(1000)

# One counter for each wake source, kept as two bytes in RTC memory. After a power-on or a reset there is no wake to
# count, so they start from 0 again.
timer_wakes = 0
button_wakes = 0
saved = rtc_mem.memory()
if machine.reset_cause() == machine.DEEPSLEEP_RESET and len(saved) >= 2:
    timer_wakes = saved[0]
    button_wakes = saved[1]

# Ask the chip what woke it, then count and blink according to the answer.
reason = machine.wake_reason()

if machine.reset_cause() != machine.DEEPSLEEP_RESET:
    # Power on or reset: three blinks so you can tell it apart from a real wake.
    blink(3)
elif reason == machine.TIMER_WAKE:
    timer_wakes = (timer_wakes + 1) & 0xFF
    blink(1)
elif reason == machine.EXT0_WAKE:
    button_wakes = (button_wakes + 1) & 0xFF
    blink(2)

print()
print("timer wakes:  {}".format(timer_wakes))
print("button wakes: {}".format(button_wakes))

# Save both counters before sleeping.
rtc_mem.memory(bytes([timer_wakes, button_wakes]))

# If the button is still held down, the pin is still LOW and the board would wake again the moment it sleeps.
# Wait here until the button is let go.
while button.value() == 0:
    time.sleep_ms(10)

# Arm the button, then sleep with a timer. Whichever comes first wakes the board.
esp32.wake_on_ext0(pin=button, level=esp32.WAKEUP_ALL_LOW)
deepsleep(SLEEP_SECONDS * 1000)
