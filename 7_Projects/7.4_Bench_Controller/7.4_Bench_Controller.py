"""
@file       7.4_Bench_Controller.py
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
breadboard. The internal pull-ups switch off during deep sleep, which T24 covers.
"""
RELAY_BUTTON_PIN = 21
BUZZER_BUTTON_PIN = 39

POT_PIN = 4

# The servo takes its power from VCC, never from 3V3. The 3V3 regulator is there to run the chip.
SERVO_PIN = 47
BUZZER_PIN = 48

RGB_PIN = 2

SDA_PIN = 8
SCL_PIN = 9

TMP117_ADDRESS = 0x49
RELAY_ADDRESS = 0x30

# From T17. Yours will be a different number.
BUZZER_HZ = 2700

# From T19. Yours will be different numbers.
PULSE_MIN_US = 550
PULSE_MAX_US = 2500
SERVO_FREQ = 50

# Your measured bounce duration from T8, rounded up.
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

relay_button = Pin(RELAY_BUTTON_PIN, Pin.IN, Pin.PULL_UP)
buzzer_button = Pin(BUZZER_BUTTON_PIN, Pin.IN, Pin.PULL_UP)

pot = ADC(Pin(POT_PIN), atten=ADC.ATTN_11DB)
rgb = neopixel.NeoPixel(Pin(RGB_PIN), 1)

servo = PWM(Pin(SERVO_PIN), freq=SERVO_FREQ)
buzzer = PWM(Pin(BUZZER_PIN), freq=BUZZER_HZ, duty_u16=0)

# Debounce state for each button, from T8. The buttons idle at 1 because of the pull-ups.
relay_button_state = 1
relay_button_last_reading = 1
relay_button_change_ms = 0

buzzer_button_state = 1
buzzer_button_last_reading = 1
buzzer_button_change_ms = 0

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

while True:
    # Five jobs, none of which waits for any of the others. Everything on the pages before this one worked in
    # isolation, and the reason all of it composes here is that no part of it blocks. Architecture is the one thing
    # that cannot be taught on a page about a single component, and it comes down to this.
    #
    # The time is read once per pass, so every job below agrees on what "now" is.
    now = time.ticks_ms()

    # Job 1: the buttons. Debouncing from T8: a reading only counts once it has stayed the same for DEBOUNCE_MS. The
    # two buttons are handled one after the other, with the same steps.
    #
    # The relay button, IO21.
    relay_reading = relay_button.value()

    if relay_reading != relay_button_last_reading:
        relay_button_last_reading = relay_reading
        relay_button_change_ms = now

    if time.ticks_diff(now, relay_button_change_ms) > DEBOUNCE_MS and relay_reading != relay_button_state:
        relay_button_state = relay_reading

        # Pull-ups mean 0 is pressed.
        if relay_reading == 0:
            last_input_ms = now

            # Closing the relay locks the controls. The ignored press further down is the point of this design: it is
            # still scanned, still debounced, and then dropped with a line saying so. A program that blocks elsewhere
            # never sees the press at all, and from the bench the two look identical. One is a decision and the other
            # is a bug, and what tells them apart is that a program which chose to ignore you can say so.
            relay_on = not relay_on

            if relay_on:
                relay.relayControl(CHANNEL1, 1)
                print("relay on, controls locked")
            else:
                relay.relayControl(CHANNEL1, 0)
                print("relay off, controls unlocked")

    # The buzzer button, IO39.
    buzzer_reading = buzzer_button.value()

    if buzzer_reading != buzzer_button_last_reading:
        buzzer_button_last_reading = buzzer_reading
        buzzer_button_change_ms = now

    if time.ticks_diff(now, buzzer_button_change_ms) > DEBOUNCE_MS and buzzer_reading != buzzer_button_state:
        buzzer_button_state = buzzer_reading

        if buzzer_reading == 0:
            last_input_ms = now

            if relay_on:
                print("locked. Press the button on IO21 to unlock.")
            else:
                buzzer_on = not buzzer_on

                if buzzer_on:
                    print("buzzer on")
                else:
                    print("buzzer off")

    # Job 2: the sensor, every 400 ms.
    if time.ticks_diff(now, last_sensor_ms) >= SENSOR_INTERVAL_MS:
        last_sensor_ms = now

        # Asked every time, so pulling the Qwiic cable out mid-run is caught on the next read rather than never.
        try:
            sensor_ok = (tmp.getDeviceID() == 0x117)
            if sensor_ok:
                temperature_c = tmp.getTemperature()
        except OSError:
            sensor_ok = False

    # Job 3: the RGB LED on the board, every 80 ms.
    if time.ticks_diff(now, last_display_ms) >= DISPLAY_INTERVAL_MS:
        last_display_ms = now

        if not sensor_ok:
            # Flashing white, so a missing sensor can never be mistaken for a reading at one end of the colour range.
            # The LED is on for 300 ms, off for 300 ms, and so on, which is what dividing the time by 300 and looking
            # at whether the result is odd or even gives you.
            if (now // 300) % 2 == 1:
                rgb[0] = (LED_BRIGHTNESS, LED_BRIGHTNESS, LED_BRIGHTNESS)
            else:
                rgb[0] = (0, 0, 0)
        elif relay_on:
            # Green appears nowhere in the gradient below, so it means one thing: the controls are locked. A state
            # that changes what the buttons do has to be visible without the console.
            rgb[0] = (0, LED_BRIGHTNESS, 0)
        else:
            # span runs from 0.0 at the cold end of the range to 1.0 at the hot end.
            span = (temperature_c - COLOUR_MIN_C) / (COLOUR_MAX_C - COLOUR_MIN_C)
            if span < 0.0:
                span = 0.0
            if span > 1.0:
                span = 1.0

            # The neopixel module takes plain red, green, blue and sorts out the GRB byte order the WS2812B wants. As
            # the room warms, red grows and blue shrinks.
            rgb[0] = (int(span * LED_BRIGHTNESS), 0, int((1.0 - span) * LED_BRIGHTNESS))

        rgb.write()

    # Job 4: the buzzer. A chirp every two seconds, written without a single blocking sleep. Two timestamps and a
    # flag do what a sleep would have done, and the needle keeps moving and the buttons keep answering while it
    # sounds.
    if not buzzer_on:
        if chirping:
            chirping = False
            buzzer.duty_u16(0)
    else:
        if not chirping and time.ticks_diff(now, last_chirp_ms) >= CHIRP_PERIOD_MS:
            chirping = True
            last_chirp_ms = now
            # Half of full scale. T17 measured loudness peaking at 50 % duty and falling again above it.
            buzzer.duty_u16(32768)

        if chirping and time.ticks_diff(now, last_chirp_ms) >= CHIRP_MS:
            chirping = False
            buzzer.duty_u16(0)

    # Job 5: the servo, every 30 ms. Locked, the pot is not read and the needle holds still, but this job keeps
    # running on its 30 ms timer either way. Stopping a job and stopping what a job does to the outside world are
    # different things.
    if time.ticks_diff(now, last_servo_ms) >= SERVO_INTERVAL_MS:
        last_servo_ms = now

        if not relay_on:
            raw = pot.read()
            target = PULSE_MIN_US + (raw * (PULSE_MAX_US - PULSE_MIN_US)) // 4095

            # Move towards the target by at most SERVO_STEP_US a time, so the needle glides.
            difference = target - current_pulse_us
            if difference < -SERVO_STEP_US:
                difference = -SERVO_STEP_US
            if difference > SERVO_STEP_US:
                difference = SERVO_STEP_US
            current_pulse_us = current_pulse_us + difference

            servo.duty_ns(current_pulse_us * 1000)

    # Sleep: two minutes without a press and the whole thing sleeps, waking on IO21. Everything it was doing is lost,
    # because deep sleep is not pausing, and the script rebuilds it on the way back. The relay is dropped first: a
    # latched coil would draw more asleep than the chip does.
    if time.ticks_diff(now, last_input_ms) >= IDLE_SLEEP_MS:
        print("idle for two minutes. Sleeping. Press the button on IO21 to wake.")

        buzzer.duty_u16(0)
        relay.relayControl(CHANNEL1, 0)
        rgb[0] = (0, 0, 0)
        rgb.write()

        esp32.wake_on_ext0(pin=relay_button, level=esp32.WAKEUP_ALL_LOW)
        deepsleep()
