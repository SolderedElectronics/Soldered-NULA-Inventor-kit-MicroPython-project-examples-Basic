"""
@file       11c_Thermostat_Needle_Gauge.py
@brief      A cooling thermostat with a needle gauge. The pot sets the temperature you want, the TMP117
            measures the room and the relay switches a fan with a 0.5 degree band either side of your
            number. The servo needle shows how far the room is from the setpoint: centre means on target,
            one side means colder and the other means warmer. The onboard LED is red while the fan runs and
            blue while it does not. If the sensor stops answering, the fan stops, the LED flashes white and
            the buzzer warbles until you press the button on IO39.
            For details, connection diagram and more, check out the example documentation at: <link placeholder>

@author     Borna Zelenika @ soldered.com
"""

from machine import Pin, I2C, ADC, PWM
import neopixel
import time

# The Soldered drivers for the TMP117 and the relay board, found in the lib folder of this repository.
from tmp117 import TMP117
from Relay import Relay, CHANNEL1

SDA_PIN = 8
SCL_PIN = 9

TMP117_ADDRESS = 0x49
RELAY_ADDRESS = 0x30

POT_PIN = 4
MUTE_PIN = 39
SERVO_PIN = 47
BUZZER_PIN = 48
RGB_PIN = 2

# From T22. Yours will be a different number.
BUZZER_HZ = 2700

# From T24. Yours will be different numbers.
PULSE_MIN_US = 550
PULSE_MAX_US = 2500
SERVO_FREQ = 50

# The pot sets the setpoint somewhere in this range, in degrees.
SETPOINT_MIN_C = 15.0
SETPOINT_MAX_C = 35.0

# The fan comes on this far above the setpoint and goes off this far below it, so a reading wobbling around the
# setpoint cannot make the relay chatter.
BAND_C = 0.5

# The needle sits at one end when the room is this far from the setpoint or more.
GAUGE_RANGE_C = 5.0

LED_BRIGHTNESS = 32

SENSOR_INTERVAL_MS = 250
SERVO_INTERVAL_MS = 30
PRINT_INTERVAL_MS = 1000
DEBOUNCE_MS = 25

# How far the needle may move on each 30 ms step, from T25, so it glides instead of jumping.
SERVO_STEP_US = 20

i2c = I2C(0, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN))

tmp = TMP117(i2c, TMP117_ADDRESS)
tmp.init(None)

relay = Relay(i2c, RELAY_ADDRESS)
relay.relayControl(CHANNEL1, 0)

pot = ADC(Pin(POT_PIN), atten=ADC.ATTN_11DB)
rgb = neopixel.NeoPixel(Pin(RGB_PIN), 1)
servo = PWM(Pin(SERVO_PIN), freq=SERVO_FREQ)
buzzer = PWM(Pin(BUZZER_PIN), freq=BUZZER_HZ, duty_u16=0)


class Button:
    """
    A button that debounces itself. The pin and the three pieces of state it needs are kept together in one unit,
    so the mute button is one object instead of a handful of loose variables.
    """

    def __init__(self, pin_number):
        self.pin = Pin(pin_number, Pin.IN, Pin.PULL_UP)
        self.stable = 1
        self.last = 1
        self.changed_ms = 0

    def was_pressed(self):
        """True exactly once for each press. The pull-up means 0 is pressed."""
        reading = self.pin.value()
        now = time.ticks_ms()

        if reading != self.last:
            self.last = reading
            self.changed_ms = now

        if time.ticks_diff(now, self.changed_ms) > DEBOUNCE_MS and reading != self.stable:
            self.stable = reading
            return self.stable == 0
        return False


mute_button = Button(MUTE_PIN)

setpoint_c = 22.0
temperature_c = 0.0
sensor_ok = False
fan_on = False
muted = False

current_pulse_us = (PULSE_MIN_US + PULSE_MAX_US) // 2

last_sensor_ms = 0
last_servo_ms = 0
last_print_ms = 0


def map_clamped(x, in_low, in_high, out_low, out_high):
    """Turns a value from one range into a position in another and never goes outside it. Used for both the
    setpoint and the needle, so neither needs its own copy of the arithmetic."""
    t = (x - in_low) / (in_high - in_low)
    t = max(0.0, min(1.0, t))
    return out_low + t * (out_high - out_low)


def read_setpoint():
    global setpoint_c

    target = map_clamped(pot.read(), 0, 4095, SETPOINT_MIN_C, SETPOINT_MAX_C)

    # Light smoothing, from earlier in the manual, so the setpoint does not jitter.
    setpoint_c = setpoint_c + 0.05 * (target - setpoint_c)


def read_sensor():
    global sensor_ok, temperature_c, last_sensor_ms

    if time.ticks_diff(time.ticks_ms(), last_sensor_ms) < SENSOR_INTERVAL_MS:
        return
    last_sensor_ms = time.ticks_ms()

    # Ask before believing. MicroPython raises when nothing answers, and the device ID catches the case where
    # something answers but is not a TMP117.
    try:
        sensor_ok = (tmp.getDeviceID() == 0x117)
        if sensor_ok:
            temperature_c = tmp.getTemperature()
    except OSError:
        sensor_ok = False


def set_fan(on):
    global fan_on

    if on == fan_on:
        return
    fan_on = on
    relay.relayControl(CHANNEL1, 1 if on else 0)


def control_fan():
    if not sensor_ok:
        set_fan(False)
        return

    # Between the two limits nothing changes, which is exactly what stops the relay from chattering.
    if temperature_c > setpoint_c + BAND_C:
        set_fan(True)
    elif temperature_c < setpoint_c - BAND_C:
        set_fan(False)


def move_needle():
    global current_pulse_us, last_servo_ms

    if time.ticks_diff(time.ticks_ms(), last_servo_ms) < SERVO_INTERVAL_MS:
        return
    last_servo_ms = time.ticks_ms()

    # With no sensor the needle goes to the middle rather than pointing at an old reading.
    error = (temperature_c - setpoint_c) if sensor_ok else 0.0
    target = int(map_clamped(error, -GAUGE_RANGE_C, GAUGE_RANGE_C, PULSE_MIN_US, PULSE_MAX_US))

    difference = max(-SERVO_STEP_US, min(SERVO_STEP_US, target - current_pulse_us))
    current_pulse_us += difference

    servo.duty_ns(current_pulse_us * 1000)


def show_led():
    if not sensor_ok:
        # Flashing white cannot be mistaken for a temperature.
        level = LED_BRIGHTNESS if (time.ticks_ms() // 300) % 2 else 0
        rgb[0] = (level, level, level)
    elif fan_on:
        rgb[0] = (LED_BRIGHTNESS, 0, 0)
    else:
        rgb[0] = (0, 0, LED_BRIGHTNESS)
    rgb.write()


def sound_alarm():
    global muted

    # A press silences the alarm, and the next fault sounds again because the mute is forgotten once the sensor
    # answers.
    if mute_button.was_pressed() and not sensor_ok:
        muted = True
    if sensor_ok:
        muted = False

    warble = (time.ticks_ms() // 300) % 2
    buzzer.duty_u16(32768 if (not sensor_ok and not muted and warble) else 0)


def report():
    global last_print_ms

    if time.ticks_diff(time.ticks_ms(), last_print_ms) < PRINT_INTERVAL_MS:
        return
    last_print_ms = time.ticks_ms()

    if not sensor_ok:
        print("SENSOR FAULT: nothing answering at 0x49. Fan off.")
        return

    print("setpoint {:.2f} C   temperature {:.2f} C   fan {}".format(
        setpoint_c, temperature_c, "ON" if fan_on else "off"))


print()
print("thermostat gauge running: needle in the middle means the room is at your number")

while True:
    read_setpoint()
    read_sensor()
    control_fan()
    move_needle()
    show_led()
    sound_alarm()
    report()
