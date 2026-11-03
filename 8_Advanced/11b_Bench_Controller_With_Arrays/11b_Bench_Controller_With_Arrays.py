"""
@file       11b_Bench_Controller_With_Arrays.py
@brief      Five jobs sharing one loop, none of them waiting for the others. A pot aims the servo, the TMP117
            colours the onboard RGB LED, and the buzzer chirps, until the relay button locks the controls and
            the LED turns green. Two idle minutes put the board to sleep.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, I2C, ADC, PWM, deepsleep, reset_cause
import machine
import esp32
import neopixel
import time

# The Soldered drivers for the TMP117 and the relay board, found in the lib folder of this repository.
from tmp117 import TMP117
from Relay import Relay, CHANNEL1

"""
Everything before this page worked on its own. This one is about making four of them work at the same time, so the
parts list is short on purpose: one pot, two buttons, the servo, the buzzer, and the two Qwiic modules. The readout
is the WS2812B already on the board.

IO21 is the button that also has to wake the board, so it is the one that needs a pull-up of its own on the
breadboard. The internal pull-ups switch off during deep sleep, which T31 covers.
"""
BUTTON_PINS = (21, 39)
BTN_RELAY = 0
BTN_BUZZER = 1

POT_PIN = 4

# The servo takes its power from VCC, never from 3V3. The 3V3 regulator is there to run the chip.
SERVO_PIN = 47
BUZZER_PIN = 48

RGB_PIN = 2

SDA_PIN = 8
SCL_PIN = 9

TMP117_ADDRESS = 0x49
RELAY_ADDRESS = 0x30

# From T22. Yours will be a different number.
BUZZER_HZ = 2700

# From T24. Yours will be different numbers.
PULSE_MIN_US = 550
PULSE_MAX_US = 2500
SERVO_FREQ = 50

# Your measured bounce duration from T9, rounded up.
DEBOUNCE_MS = 25

IDLE_SLEEP_MS = 120000

# Three different rates, none allowed to hold up the others. The buttons are faster than all of them because they
# are read on every single pass.
SENSOR_INTERVAL_MS = 400
DISPLAY_INTERVAL_MS = 80
SERVO_INTERVAL_MS = 30

# At 20 us a step the needle crosses its whole range in about three seconds. This is the number to change first if
# the sweep feels wrong on your bench.
SERVO_STEP_US = 20

# The colour runs blue to red across this span. Pick a range your room actually sits inside.
COLOUR_MIN_C = 20.0
COLOUR_MAX_C = 30.0

# The WS2812B is far brighter than it needs to be. This is an eighth of full scale.
LED_BRIGHTNESS = 32

CHIRP_MS = 120
CHIRP_PERIOD_MS = 2000

first_boot = (reset_cause() != machine.DEEPSLEEP_RESET)

# Only the first boot waits for a console: it survives deep sleep here because the CH340 stays enumerated.
if first_boot:
    time.sleep_ms(1000)

i2c = I2C(0, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN))

# Nothing else is configured: every setConvMode, setConvTime, setAveraging and setAlertMode call writes the
# sensor's EEPROM, and doing that on each boot of a board that sleeps all day is a lot of writes for no gain.
tmp = TMP117(i2c, TMP117_ADDRESS)
tmp.init(None)

relay = Relay(i2c, RELAY_ADDRESS)
relay.relayControl(CHANNEL1, 0)

buttons = [Pin(p, Pin.IN, Pin.PULL_UP) for p in BUTTON_PINS]

pot = ADC(Pin(POT_PIN), atten=ADC.ATTN_11DB)
rgb = neopixel.NeoPixel(Pin(RGB_PIN), 1)

servo = PWM(Pin(SERVO_PIN), freq=SERVO_FREQ)
buzzer = PWM(Pin(BUZZER_PIN), freq=BUZZER_HZ, duty_u16=0)

# Debounce state, one set per button, from T9.
button_state = [1] * len(BUTTON_PINS)
last_reading = [1] * len(BUTTON_PINS)
last_change_ms = [0] * len(BUTTON_PINS)
button_pressed = [False] * len(BUTTON_PINS)

temperature_c = 0.0
sensor_ok = False
relay_on = False
buzzer_on = False
chirping = False

last_input_ms = time.ticks_ms()
last_sensor_ms = 0
last_display_ms = 0
last_servo_ms = 0
last_chirp_ms = 0

current_pulse_us = (PULSE_MIN_US + PULSE_MAX_US) // 2

print()
print("bench controller. pot aims the needle, IO39 toggles the buzzer, IO21 closes the relay and locks both.")
if not first_boot:
    print("woken by a button press.")


def service_buttons():
    """Debouncing from T9, in the form you actually want it: a function that reports a press once and then forgets
    it, so the code reacting to a button never has to think about timing."""
    global last_input_ms

    now = time.ticks_ms()

    for i in range(len(BUTTON_PINS)):
        reading = buttons[i].value()

        if reading != last_reading[i]:
            last_reading[i] = reading
            last_change_ms[i] = now

        if time.ticks_diff(now, last_change_ms[i]) > DEBOUNCE_MS and reading != button_state[i]:
            button_state[i] = reading

            # Pull-ups mean LOW is pressed.
            if reading == 0:
                button_pressed[i] = True
                last_input_ms = now


def take_press(index):
    if not button_pressed[index]:
        return False
    button_pressed[index] = False
    return True


def service_sensor():
    global sensor_ok, temperature_c, last_sensor_ms

    if time.ticks_diff(time.ticks_ms(), last_sensor_ms) < SENSOR_INTERVAL_MS:
        return
    last_sensor_ms = time.ticks_ms()

    # Asked every time, so pulling the Qwiic cable out mid-run is caught on the next read rather than never.
    try:
        sensor_ok = (tmp.getDeviceID() == 0x117)
        if sensor_ok:
            temperature_c = tmp.getTemperature()
    except OSError:
        sensor_ok = False


def service_controls():
    """
    Closing the relay locks the controls. The ignored press is the point of this function: it is still scanned,
    still debounced, still taken off the queue, and then dropped with a line saying so. A program that blocks
    elsewhere never sees the press at all, and from the bench the two look identical. One is a decision and the
    other is a bug, and what tells them apart is that a program which chose to ignore you can say so.
    """
    global relay_on, buzzer_on

    if take_press(BTN_RELAY):
        relay_on = not relay_on
        relay.relayControl(CHANNEL1, 1 if relay_on else 0)
        print("relay {}{}".format(
            "on" if relay_on else "off",
            ", controls locked" if relay_on else ", controls unlocked"))

    if take_press(BTN_BUZZER):
        if relay_on:
            print("locked. Press the button on IO21 to unlock.")
        else:
            buzzer_on = not buzzer_on
            print("buzzer {}".format("on" if buzzer_on else "off"))


def service_display():
    global last_display_ms

    if time.ticks_diff(time.ticks_ms(), last_display_ms) < DISPLAY_INTERVAL_MS:
        return
    last_display_ms = time.ticks_ms()

    if not sensor_ok:
        # Flashing white, so a missing sensor can never be mistaken for a reading at one end of the colour range.
        on = (time.ticks_ms() // 300) % 2
        level = LED_BRIGHTNESS if on else 0
        rgb[0] = (level, level, level)
    elif relay_on:
        # Green appears nowhere in the gradient below, so it means one thing: the controls are locked. A state that
        # changes what the buttons do has to be visible without the console.
        rgb[0] = (0, LED_BRIGHTNESS, 0)
    else:
        span = (temperature_c - COLOUR_MIN_C) / (COLOUR_MAX_C - COLOUR_MIN_C)
        span = max(0.0, min(1.0, span))

        # The neopixel module takes plain red, green, blue and sorts out the GRB byte order the WS2812B wants.
        rgb[0] = (int(span * LED_BRIGHTNESS), 0, int((1.0 - span) * LED_BRIGHTNESS))

    rgb.write()


def service_buzzer():
    """A chirp every two seconds, written without a single blocking sleep. Two timestamps and a flag do what a
    sleep would have done, and the needle keeps moving and the buttons keep answering while it sounds."""
    global chirping, last_chirp_ms

    if not buzzer_on:
        if chirping:
            chirping = False
            buzzer.duty_u16(0)
        return

    now = time.ticks_ms()

    if not chirping and time.ticks_diff(now, last_chirp_ms) >= CHIRP_PERIOD_MS:
        chirping = True
        last_chirp_ms = now
        # Half of full scale. T22 measured loudness peaking at 50 % duty and falling again above it.
        buzzer.duty_u16(32768)

    if chirping and time.ticks_diff(now, last_chirp_ms) >= CHIRP_MS:
        chirping = False
        buzzer.duty_u16(0)


def service_outputs():
    global current_pulse_us, last_servo_ms

    service_buzzer()

    if time.ticks_diff(time.ticks_ms(), last_servo_ms) < SERVO_INTERVAL_MS:
        return
    last_servo_ms = time.ticks_ms()

    # Locked, the pot is not read and the needle holds still, but this job keeps running on its 30 ms timer either
    # way. Stopping a job and stopping what a job does to the outside world are different things.
    if relay_on:
        return

    raw = pot.read()
    target = PULSE_MIN_US + (raw * (PULSE_MAX_US - PULSE_MIN_US)) // 4095

    difference = target - current_pulse_us
    difference = max(-SERVO_STEP_US, min(SERVO_STEP_US, difference))
    current_pulse_us += difference

    servo.duty_ns(current_pulse_us * 1000)


def service_sleep():
    """Two minutes without a press and the whole thing sleeps, waking on IO21. Everything it was doing is lost,
    because deep sleep is not pausing, and the script rebuilds it on the way back. The relay is dropped first: a
    latched coil would draw more asleep than the chip does."""
    if time.ticks_diff(time.ticks_ms(), last_input_ms) < IDLE_SLEEP_MS:
        return

    print("idle for two minutes. Sleeping. Press the button on IO21 to wake.")

    buzzer.duty_u16(0)
    relay.relayControl(CHANNEL1, 0)
    rgb[0] = (0, 0, 0)
    rgb.write()

    esp32.wake_on_ext0(pin=buttons[BTN_RELAY], level=esp32.WAKEUP_ALL_LOW)
    deepsleep()


while True:
    # Five jobs, none of which waits for any of the others. Everything on the pages before this one worked in
    # isolation, and the reason all of it composes here is that no part of it blocks. Architecture is the one thing
    # that cannot be taught on a page about a single component, and it comes down to this.
    service_buttons()
    service_sensor()
    service_controls()
    service_display()
    service_outputs()
    service_sleep()
